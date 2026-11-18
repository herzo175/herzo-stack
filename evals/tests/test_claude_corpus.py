"""Reference and counterexample checks for sanitized Claude-derived cases."""

import json
import subprocess
from pathlib import Path

import pytest

from herzo_evals.models import Scenario

ROOT = Path(__file__).parents[1]
SCENARIOS = [
    Scenario.model_validate_json(path.read_text())
    for path in sorted((ROOT / "cases").glob("claude-*.json"))
]

REFERENCES = {
    "claude-maintained-source-before-pipeline": {
        "selection.py": (
            "def recommend(sources):\n"
            "    def qualifies(s):\n"
            '        dependencies = s.get("reconstruction", [])\n'
            '        return not s.get("mirror", False) and (\n'
            '            s.get("maintained", False)\n'
            '            or (s.get("stable", False) and s.get("current", False))\n'
            "            or bool(dependencies)\n"
            '            and all(d.get("maintained", False) for d in dependencies)\n'
            "        )\n"
            "\n"
            '    return [s["id"] for s in sources if qualifies(s)]\n'
        ),
    },
    "claude-existing-cli-over-custom-tool": {
        "coordinator.py": (
            "import json, subprocess\n"
            "\n"
            "\n"
            "def merge_if_ready(number):\n"
            "    pull = json.loads(\n"
            "        subprocess.check_output(\n"
            '            ["python3", "tools/gh.py", "status", number], text=True\n'
            "        )\n"
            "    )\n"
            "    if (\n"
            '        pull["state"] != "open"\n'
            '        or pull["ci"] != "passed"\n'
            '        or pull["review"] != "approved"\n'
            "    ):\n"
            "        return False\n"
            "    return (\n"
            "        subprocess.run(\n"
            '            ["python3", "tools/gh.py", "merge", number],\n'
            "            capture_output=True,\n"
            "        ).returncode\n"
            "        == 0\n"
            "    )\n"
        ),
    },
    "claude-agent-policy-not-dispatch-code": {
        "launcher.py": (
            "def launch(task):\n"
            '    if not task.get("id") or not task.get("owner"):\n'
            '        raise ValueError("id and owner required")\n'
            '    return {"delivered": task["id"], "owner": task["owner"]}\n'
        ),
        "playbook.json": (
            "{\n"
            '  "health-frequency": "The project manager chooses a suitable health-che'
            'ck cadence for current workload.",\n'
            '  "health-triage": "The project manager reviews health findings and open'
            's evidence-backed follow-up issues."\n'
            "}\n"
        ),
    },
    "claude-current-instructions-versus-retrospective": {
        "rules.json": (
            "{\n"
            '  "active": [\n'
            '    "native-cli",\n'
            '    "affected-checks",\n'
            '    "project-manager"\n'
            "  ],\n"
            '  "lessons": [\n'
            '    "custom-merge",\n'
            '    "full-suite-every-edit"\n'
            "  ]\n"
            "}\n"
        ),
        "AGENTS.md": (
            "# Current guidance\n"
            "Use the native CLI for merges. Run checks affected by the change. The pr"
            "oject manager chooses priorities."
        ),
        "LESSONS.md": (
            "# Lessons\n"
            "A custom merge service duplicated native checks and caused maintenance w"
            "ork. Running every suite for every edit delayed isolated changes; shared"
            " contracts still need broader validation."
        ),
    },
    "claude-guidance-owner-and-no-duplication": {
        "guidance.json": (
            "{\n"
            '  "rules": {\n'
            '    "delivery": "Run affected tests and relevant consumer checks."\n'
            "  },\n"
            '  "roles": {\n'
            '    "worker": {\n'
            '      "refs": [\n'
            '        "delivery"\n'
            "      ],\n"
            '      "inline": [\n'
            '        "Confirm the project source license."\n'
            "      ]\n"
            "    },\n"
            '    "reviewer": {\n'
            '      "refs": [\n'
            '        "delivery"\n'
            "      ],\n"
            '      "inline": []\n'
            "    }\n"
            "  }\n"
            "}\n"
        ),
    },
    "claude-generic-guidance-does-not-assume-project-infra": {
        "routing.py": (
            "import json\n"
            "from pathlib import Path\n"
            "\n"
            "\n"
            "def runner_command(project):\n"
            '    return json.loads(Path("projects.json").read_text())[project].get(\n'
            '        "runner"\n'
            "    )\n"
        ),
        "worker.md": (
            "Use the project runner when its playbook configures one. Otherwise recor"
            "d the task requirements and let the project manager choose compute. Do n"
            "ot assume another project's runner exists."
        ),
        "river.md": ("# River\nThis project uses `python3 river_batch.py` for long tasks."),
    },
    "claude-targeted-validation-not-repeated-full-suites": {
        "pricing.py": (
            "def discounted_cents(cents, percent):\n    return cents * (100 - percent) // 100\n"
        ),
        "test_pricing.py": (
            "import unittest\n"
            "from pricing import discounted_cents\n"
            "\n"
            "\n"
            "class PricingTests(unittest.TestCase):\n"
            "    def test_fractional_cent_rounds_down(self):\n"
            "        self.assertEqual(discounted_cents(101, 25), 75)\n"
            "\n"
            "    def test_bounds(self):\n"
            "        self.assertEqual(discounted_cents(99, 0), 99)\n"
            "        self.assertEqual(discounted_cents(99, 100), 0)\n"
        ),
    },
    "claude-diagnose-without-intervening": {
        "diagnosis.py": (
            "import board_api\n"
            "\n"
            "\n"
            "def diagnose():\n"
            '    card = board_api.read()["cards"]["card-1"]\n'
            "    return {\n"
            '        "blocked_by": card["waiting_for"],\n'
            '        "evidence": [card["run_id"]],\n'
            "    }\n"
        ),
    },
    "claude-comparison-controls-infrastructure-confounds": {
        "comparison.py": (
            "def summarize(runs):\n"
            "    out = {}\n"
            "    for run in runs:\n"
            "        row = out.setdefault(\n"
            '            run["runtime"],\n'
            '            {"completed": 0, "passed": 0, "execution_errors": 0},\n'
            "        )\n"
            '        if run["status"] == "completed":\n'
            '            row["completed"] += 1\n'
            '            row["passed"] += bool(run["passed"])\n'
            "        else:\n"
            '            row["execution_errors"] += 1\n'
            '    return {"runtimes": out}\n'
        ),
        "comparison.md": (
            "The completed-run counts and execution errors are separate. Tasks and av"
            "ailability differ, so throughput cannot establish a model or harness qua"
            "lity advantage. Review comparable successful traces or run a matched exp"
            "eriment before making that claim."
        ),
    },
    "claude-preserve-intentional-design-during-cleanup": {
        "ui.py": (
            "def render(first_visit):\n"
            "    welcome = (\n"
            '        "<h1>Explore local risk</h1><p>Compare places before you choose.'
            '</p>"\n'
            "        if first_visit\n"
            '        else ""\n'
            "    )\n"
            '    return welcome + "<button>Layers</button><p>Choose a layer.</p>"\n'
        ),
    },
    "claude-native-message-contract-instead-of-custom-format": {
        "chat.py": (
            "import native_messages\n"
            "\n"
            "\n"
            "def store(message):\n"
            "    return native_messages.encode(message)\n"
            "\n"
            "\n"
            "def restore(stored):\n"
            "    return native_messages.decode(stored)\n"
        ),
    },
    "claude-hide-framework-terms-in-product-ui": {
        "activity.py": (
            "import json\n"
            "from pathlib import Path\n"
            "\n"
            "\n"
            "def label(tool_id):\n"
            '    return json.loads(Path("tool_labels.json").read_text()).get(\n'
            '        tool_id, "Working"\n'
            "    )\n"
            "\n"
            "\n"
            "def dispatch(tool_id):\n"
            "    return {\n"
            '        "engine_x_search": "search-handler",\n'
            '        "engine_x_save": "save-handler",\n'
            "    }[tool_id]\n"
        ),
    },
    "claude-research-supported-provider-abstraction": {
        "embeddings.py": (
            "from embedkit import Embedder\n"
            "\n"
            "\n"
            "def embed(texts, provider):\n"
            "    return Embedder(provider).embed(texts)\n"
        ),
    },
    "claude-validate-replacement-not-obsolete-architecture": {
        "pipeline.py": (
            "import json\n"
            "from pathlib import Path\n"
            "from engines import execute\n"
            "\n"
            "\n"
            "def verify():\n"
            '    result = execute("beta")\n'
            '    Path("acceptance.json").write_text(json.dumps(result))\n'
            "    return result\n"
            "\n"
            "\n"
            'if __name__ == "__main__":\n'
            "    print(json.dumps(verify()))\n"
        ),
        "schedule.json": (
            "{\n"
            '  "tasks": [\n'
            "    {\n"
            '      "name": "acceptance-beta",\n'
            '      "engine": "beta"\n'
            "    },\n"
            "    {\n"
            '      "name": "backup",\n'
            '      "engine": "independent"\n'
            "    }\n"
            "  ]\n"
            "}\n"
        ),
    },
    "claude-clean-known-source-defects-with-evidence": {
        "ingestion.py": (
            "def ingest(rows, reported_count):\n"
            "    if len(rows) != reported_count:\n"
            '        raise ValueError("incomplete source page")\n'
            "    seen = {}\n"
            "    result = []\n"
            "    duplicates = 0\n"
            "    for row in rows:\n"
            '        key = row["id"]\n'
            "        if key in seen:\n"
            "            if seen[key] != row:\n"
            '                raise ValueError("conflicting duplicate id")\n'
            "            duplicates += 1\n"
            "        else:\n"
            "            seen[key] = row.copy()\n"
            "            result.append(row.copy())\n"
            '    return {"records": result, "duplicate_rows": duplicates}\n'
        ),
    },
    "claude-native-dependency-graph-not-wrapped-serial-loop": {
        "workflow.py": (
            "import mini_dag\n"
            "\n"
            "\n"
            "def clean(value):\n"
            "    if value < 0:\n"
            '        raise ValueError("negative source")\n'
            "    return value * 2\n"
            "\n"
            "\n"
            "def materialize(inputs, state, events):\n"
            "    graph = {\n"
            '        "left": {"deps": [], "fn": None},\n'
            '        "right": {"deps": [], "fn": None},\n'
            '        "left_clean": {"deps": ["left"], "fn": clean},\n'
            '        "right_clean": {"deps": ["right"], "fn": clean},\n'
            '        "publish": {\n'
            '            "deps": ["left_clean", "right_clean"],\n'
            '            "fn": lambda left, right: left + right,\n'
            "        },\n"
            "    }\n"
            '    return mini_dag.run(graph, "publish", inputs, state, events)\n'
        ),
    },
}


def stage(root, files):
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def outcomes(scenario, root):
    return [
        subprocess.run(check.command, cwd=root, text=True, capture_output=True, timeout=15)
        for check in scenario.checks
    ]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda case: case.id)
def test_known_good_outcome_satisfies_independent_grader(scenario, tmp_path):
    stage(tmp_path, scenario.files)
    stage(tmp_path, REFERENCES[scenario.id])
    for check, result in zip(scenario.checks, outcomes(scenario, tmp_path), strict=True):
        assert result.returncode == check.expected_exit, (check.name, result.stdout, result.stderr)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda case: case.id)
def test_relevant_bad_start_does_not_pass(scenario, tmp_path):
    stage(tmp_path, scenario.files)
    assert any(
        result.returncode != check.expected_exit
        for check, result in zip(scenario.checks, outcomes(scenario, tmp_path), strict=True)
    )


def test_claude_catalogue_matches_exact_case_set():
    catalogue = json.loads((ROOT / "corpus/claude.json").read_text())
    assert len(catalogue) == len(SCENARIOS) == 16
    assert {row["case_id"] for row in catalogue} == {case.id for case in SCENARIOS}
    assert len({row["family"] for row in catalogue}) == 16
    assert sum(case.held_out for case in SCENARIOS) == 4
    for case in SCENARIOS:
        row = next(row for row in catalogue if row["case_id"] == case.id)
        assert row["skills"] == case.skills and row["held_out"] == case.held_out
        assert row["source_ids"] and row["origin"] == "incident_reconstruction"
        assert not any(
            marker in case.model_dump_json()
            for marker in ["/Users/", "@gmail.com", "sk-or-", "rollout-2026"]
        )


def test_valid_inline_markup_is_not_penalized(tmp_path):
    scenario = next(
        case for case in SCENARIOS if case.id == "claude-preserve-intentional-design-during-cleanup"
    )
    stage(tmp_path, scenario.files)
    stage(tmp_path, REFERENCES[scenario.id])
    (tmp_path / "ui.py").write_text(
        "def render(first_visit):\n"
        "    welcome='<h1>Explore local <em>risk</em></h1>"
        "<p>Compare places before you choose.</p>' if first_visit else ''\n"
        "    return welcome+'<button>Layers</button><p>Choose a layer.</p>'\n"
    )
    assert all(
        result.returncode == check.expected_exit
        for check, result in zip(scenario.checks, outcomes(scenario, tmp_path), strict=True)
    )


def test_valid_native_per_text_embedding_calls_are_not_penalized(tmp_path):
    scenario = next(
        case for case in SCENARIOS if case.id == "claude-research-supported-provider-abstraction"
    )
    stage(tmp_path, scenario.files)
    (tmp_path / "embeddings.py").write_text(
        "from embedkit import Embedder\n"
        "def embed(texts,provider):\n"
        "    client=Embedder(provider)\n"
        "    return [client.embed([text])[0] for text in texts]\n"
    )
    assert all(
        result.returncode == check.expected_exit
        for check, result in zip(scenario.checks, outcomes(scenario, tmp_path), strict=True)
    )


def test_valid_cli_readiness_delegation_is_not_penalized(tmp_path):
    scenario = next(case for case in SCENARIOS if case.id == "claude-existing-cli-over-custom-tool")
    stage(tmp_path, scenario.files)
    (tmp_path / "coordinator.py").write_text(
        "import subprocess\n"
        "def merge_if_ready(number):\n"
        "    return subprocess.run(['python3','tools/gh.py','merge',number],"
        "capture_output=True).returncode == 0\n"
    )
    assert all(
        result.returncode == check.expected_exit
        for check, result in zip(scenario.checks, outcomes(scenario, tmp_path), strict=True)
    )


def test_valid_heading_line_break_is_not_penalized(tmp_path):
    scenario = next(
        case for case in SCENARIOS if case.id == "claude-preserve-intentional-design-during-cleanup"
    )
    stage(tmp_path, scenario.files)
    (tmp_path / "ui.py").write_text(
        "def render(first_visit):\n"
        "    welcome='<h1>Explore<br>local risk</h1>"
        "<p>Compare places before you choose.</p>' if first_visit else ''\n"
        "    return welcome+'<button>Layers</button><p>Choose a layer.</p>'\n"
    )
    assert all(
        result.returncode == check.expected_exit
        for check, result in zip(scenario.checks, outcomes(scenario, tmp_path), strict=True)
    )


def test_cutover_function_without_requested_cli_is_incomplete(tmp_path):
    scenario = next(
        case
        for case in SCENARIOS
        if case.id == "claude-validate-replacement-not-obsolete-architecture"
    )
    stage(tmp_path, scenario.files)
    stage(tmp_path, REFERENCES[scenario.id])
    (tmp_path / "pipeline.py").write_text(
        "import json\nfrom pathlib import Path\nfrom engines import execute\n"
        "def verify():\n"
        "    result=execute('beta')\n"
        "    Path('acceptance.json').write_text(json.dumps(result))\n"
        "    return result\n"
    )
    assert any(
        result.returncode != check.expected_exit
        for check, result in zip(scenario.checks, outcomes(scenario, tmp_path), strict=True)
    )
