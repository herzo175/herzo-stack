"""Run comparable experiments without replacing the coding agents' own loops."""

import hashlib
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any

from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_evals import Case, Dataset
from pydantic_evals.lifecycle import CaseLifecycle
from pydantic_evals.reporting import ReportCase

from herzo_evals.grading import JUDGE_INPUT_LIMIT_CHARS, BehaviorJudge, OutcomeChecks
from herzo_evals.models import Scenario, Settings, TrialResult


def load_scenarios(directory: Path, ids: list[str], include_held_out: bool) -> list[Scenario]:
    cases = [
        Scenario.model_validate_json(path.read_text()) for path in sorted(directory.glob("*.json"))
    ]
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Duplicate scenario IDs")
    missing = set(ids) - {case.id for case in cases}
    if missing:
        raise ValueError(f"Unknown scenario IDs: {', '.join(sorted(missing))}")
    selected = [
        case
        for case in cases
        if (not ids or case.id in ids) and (include_held_out or not case.held_out)
    ]
    if not selected:
        raise ValueError("No scenarios selected")
    return selected


def redact(value: Any, secret: str) -> Any:
    if isinstance(value, str):
        return value.replace(secret, "[REDACTED]") if secret else value
    if isinstance(value, dict):
        return {redact(key, secret): redact(item, secret) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, secret) for item in value]
    return value


def skill_fingerprint(root: Path | None, scenarios: list[Scenario]) -> str:
    if root is None:
        return "no-skills"
    digest = hashlib.sha256()
    for name in sorted({name for case in scenarios for name in case.skills}):
        skill = root / name
        if not (skill / "SKILL.md").is_file():
            raise ValueError(f"Missing skill {name}")
        for path in sorted(skill.rglob("*")):
            if path.is_symlink():
                raise ValueError("Skill resources must not be symlinks")
            if path.is_file():
                digest.update(
                    str(path.relative_to(root)).encode() + b"\0" + path.read_bytes() + b"\0"
                )
    return digest.hexdigest()


def result_row(case: ReportCase) -> dict[str, Any]:
    return {
        "case": case.name,
        "trial_id": case.output.trial_id,
        "status": case.output.status,
        "duration_seconds": case.output.duration,
        "compactions": case.output.compactions,
        "usage": case.output.usage,
        "assertions": {
            name: {"passed": bool(reason.value), "reason": reason.reason}
            for name, reason in case.assertions.items()
        },
    }


async def run_experiment(
    scenarios: list[Scenario],
    settings: Settings,
    output: Path,
    repeat: int,
    concurrency: int,
    label: str,
    *,
    judge: bool = True,
) -> list[dict[str, Any]]:
    from herzo_evals.runtime import execute

    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise ValueError("OPENROUTER_API_KEY is required")
    output.mkdir(parents=True, exist_ok=False)
    fingerprint = skill_fingerprint(settings.skills_root, scenarios)
    image_id = subprocess.run(
        ["docker", "image", "inspect", settings.image, "--format", "{{.Id}}"],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    ).stdout.strip()
    metadata = {
        "label": label,
        "settings": settings.model_dump(mode="json"),
        "skills_sha256": fingerprint,
        "image_id": image_id,
        "case_ids": [case.id for case in scenarios],
        "cases_sha256": hashlib.sha256(
            json.dumps([case.model_dump() for case in scenarios], sort_keys=True).encode()
        ).hexdigest(),
        "usage_scope": "agent-reported; excludes judge and may omit compaction",
        "judge_input_limit_chars": JUDGE_INPUT_LIMIT_CHARS,
        "repeat": repeat,
        "concurrency": concurrency,
    }
    (output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    evaluations = [OutcomeChecks()]
    if judge:
        model = OpenRouterModel(settings.judge_model, provider=OpenRouterProvider(api_key=key))
        evaluations.append(BehaviorJudge(model=model))
    dataset = Dataset(
        name="herzo-stack",
        cases=[Case(name=case.id, inputs=case) for case in scenarios],
        evaluators=evaluations,
    )

    async def task(scenario: Scenario) -> TrialResult:
        trial_id = f"{scenario.id}-{uuid.uuid4().hex[:10]}"
        trial_dir = output / trial_id
        trial_dir.mkdir()
        # Native adapter owns process/container cancellation, including checks and extraction.
        result = await execute(scenario, settings, trial_dir)
        result = TrialResult.model_validate(redact(result.model_dump(), key))
        result.trial_id = trial_id
        (trial_dir / "result.json").write_text(result.model_dump_json(indent=2) + "\n")
        return result

    class SaveCompletedCase(CaseLifecycle):
        async def teardown(self, case: Any) -> None:
            if isinstance(case, ReportCase):
                target = output / case.output.trial_id / "verdict.json"
                target.write_text(json.dumps(redact(result_row(case), key), indent=2) + "\n")

    report = await dataset.evaluate(
        task,
        name=label,
        max_concurrency=concurrency,
        repeat=repeat,
        progress=False,
        metadata=metadata,
        lifecycle=SaveCompletedCase,
    )
    rows = [result_row(case) for case in report.cases]
    for failure in report.failures:
        rows.append({"case": failure.name, "status": "evaluation_error"})
    (output / "summary.json").write_text(json.dumps(redact(rows, key), indent=2) + "\n")
    return rows


async def paired_experiment(
    scenarios: list[Scenario],
    settings: Settings,
    baseline_root: Path | None,
    output: Path,
    repeat: int,
    concurrency: int,
    *,
    judge: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    # Alternate order across invocations if desired; never change runtime/model between arms.
    arms = {}
    for label, root in [("baseline", baseline_root), ("candidate", settings.skills_root)]:
        arms[label] = await run_experiment(
            scenarios,
            settings.model_copy(update={"skills_root": root}),
            output / label,
            repeat,
            concurrency,
            label,
            judge=judge,
        )
    return arms
