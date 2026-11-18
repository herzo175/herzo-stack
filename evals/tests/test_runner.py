import json
import subprocess
import sys
from types import SimpleNamespace

import pytest
from pydantic_ai.models.test import TestModel
from pydantic_evals import Case, Dataset

from herzo_evals.cli import snapshot_skills
from herzo_evals.grading import BehaviorJudge
from herzo_evals.models import Check, CheckResult, Scenario, Settings, TrialResult
from herzo_evals.runner import load_scenarios, run_experiment, skill_fingerprint


@pytest.fixture
def scenario():
    return Scenario(
        id="sample",
        kind="checkpoint",
        skills=["deslop"],
        prompts=["Edit this draft"],
        files={"draft.md": "It may help."},
        checks=[Check(name="meaning", command=["true"])],
        rubric="Preserve uncertainty and the original meaning.",
        provenance="Synthetic test",
    )


async def test_real_pydantic_judge_accepts_structured_evidence(scenario):
    async def task(_):
        return TrialResult(status="completed", final_response="It may help.")

    judge = BehaviorJudge(
        model=TestModel(
            custom_output_args={
                "score": 1.0,
                "pass": True,
                "reason": "Uncertainty preserved in final response",
            }
        )
    )
    report = await Dataset(
        name="judge-integration", cases=[Case(inputs=scenario)], evaluators=[judge]
    ).evaluate(task, progress=False)
    assert report.cases[0].assertions["behavior"].value is True


async def test_repetitions_persist_evidence_and_remove_secret(scenario, tmp_path, monkeypatch):
    key = "private-test-key-do-not-persist"
    monkeypatch.setenv("OPENROUTER_API_KEY", key)
    calls = []

    async def execute(case, settings, output):
        calls.append(output)
        return TrialResult(
            status="completed",
            final_response=f"echoed {key}",
            checks=[
                CheckResult(name="meaning", passed=True, exit_code=0, output="ok"),
            ],
        )

    monkeypatch.setitem(sys.modules, "herzo_evals.runtime", SimpleNamespace(execute=execute))
    monkeypatch.setattr(subprocess, "run", lambda *_, **__: SimpleNamespace(stdout="sha256:fake"))
    settings = Settings(
        runtime="pi", model="provider/agent", judge_model="provider/judge", skills_root=None
    )
    rows = await run_experiment(
        [scenario], settings, tmp_path / "arm", 2, 1, "baseline", judge=False
    )
    assert len(rows) == 2
    assert len(set(calls)) == 2
    for row in rows:
        evidence = tmp_path / "arm" / row["trial_id"] / "result.json"
        assert evidence.is_file()
        assert json.loads(evidence.read_text())["trial_id"] == row["trial_id"]
        verdict = evidence.with_name("verdict.json")
        assert json.loads(verdict.read_text()) == row
    for path in (tmp_path / "arm").rglob("*.json"):
        assert key not in path.read_text()
    assert all(row["assertions"]["check_meaning"]["passed"] for row in rows)


def test_skill_fingerprint_records_content_not_only_revision(tmp_path, scenario):
    skill = tmp_path / "deslop"
    skill.mkdir()
    (skill / "SKILL.md").write_text("version one")
    first = skill_fingerprint(tmp_path, [scenario])
    (skill / "SKILL.md").write_text("version two")
    assert skill_fingerprint(tmp_path, [scenario]) != first
    (skill / "link").symlink_to("/etc/passwd")
    with pytest.raises(ValueError, match="symlink"):
        skill_fingerprint(tmp_path, [scenario])


def test_held_out_excluded_and_unknown_id_rejected(tmp_path, scenario):
    case = scenario.model_copy(update={"held_out": True})
    (tmp_path / "case.json").write_text(case.model_dump_json())
    with pytest.raises(ValueError, match="No scenarios"):
        load_scenarios(tmp_path, [], False)
    assert load_scenarios(tmp_path, [], True)[0].held_out
    with pytest.raises(ValueError, match="Unknown"):
        load_scenarios(tmp_path, ["missing"], True)


def test_baseline_snapshot_is_exact_and_contains_only_skill_tree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
    skill = repo / "skills/deslop/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("original skill")
    (repo / "private-reference.txt").write_text("not an agent resource")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Eval",
            "-c",
            "user.email=eval@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "Initial skill",
        ],
        check=True,
    )
    revision = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    skill.write_text("changed working tree")
    destination = tmp_path / "baseline"
    destination.mkdir()
    assert snapshot_skills(repo, revision, destination) == revision
    assert (destination / "skills/deslop/SKILL.md").read_text() == "original skill"
    assert not (destination / "private-reference.txt").exists()


def test_fixture_paths_cannot_escape_or_override_agent_resources(scenario):
    for path in ["../escape", "/escape", ".git/config", ".pi/settings.json", "..\\escape"]:
        data = scenario.model_dump()
        data["files"] = {path: "bad"}
        with pytest.raises(ValueError, match="Unsafe"):
            Scenario.model_validate(data)


async def test_completed_case_verdict_survives_later_cancellation(scenario, tmp_path, monkeypatch):
    import asyncio

    monkeypatch.setenv("OPENROUTER_API_KEY", "private-key")
    started_second = asyncio.Event()
    count = 0

    async def execute(case, settings, output):
        nonlocal count
        count += 1
        if count == 2:
            started_second.set()
            await asyncio.Event().wait()
        return TrialResult(
            status="completed",
            checks=[
                CheckResult(name="meaning", passed=True, exit_code=0, output="ok"),
            ],
        )

    monkeypatch.setitem(sys.modules, "herzo_evals.runtime", SimpleNamespace(execute=execute))
    monkeypatch.setattr(subprocess, "run", lambda *_, **__: SimpleNamespace(stdout="sha256:fake"))
    settings = Settings(
        runtime="pi", model="provider/agent", judge_model="provider/judge", skills_root=None
    )
    run = asyncio.create_task(
        run_experiment(
            [scenario],
            settings,
            tmp_path / "arm",
            2,
            1,
            "candidate",
            judge=False,
        )
    )
    await asyncio.wait_for(started_second.wait(), timeout=3)
    run.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run
    verdicts = list((tmp_path / "arm").glob("*/verdict.json"))
    assert len(verdicts) == 1
    assert json.loads(verdicts[0].read_text())["assertions"]["check_meaning"]["passed"]
    assert not (tmp_path / "arm/summary.json").exists()
