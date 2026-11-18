"""Check curated tasks against independent graders and known working outcomes."""

import subprocess
from pathlib import Path

import pytest

from herzo_evals.models import Scenario

CASES = Path(__file__).parents[1] / "cases"
SCENARIOS = [Scenario.model_validate_json(p.read_text()) for p in sorted(CASES.glob("*.json"))]
RANKING = """import argparse, json

def normalize_name(name):
    return " ".join(name.split())

def rank_rows(rows, min_score=0):
    result = []
    for row in rows:
        if not isinstance(row.get("name"), str) or type(row.get("score")) is not int:
            raise ValueError("Expected string name and integer score")
        if row["score"] >= min_score:
            result.append({**row, "name": normalize_name(row["name"])})
    return sorted(result, key=lambda r: (-r["score"], r["name"]))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("destination")
    p.add_argument("--min-score", type=int, default=0)
    p.add_argument("--limit", type=int)
    a = p.parse_args()
    if a.limit is not None and a.limit < 0:
        p.error("limit must be nonnegative")
    with open(a.source) as f:
        payload = json.load(f)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        p.error("Expected an object containing items")
    rows = rank_rows(payload["items"], a.min_score)
    if a.limit is not None:
        rows = rows[:a.limit]
    with open(a.destination, "w") as f:
        json.dump({"items": rows}, f)
"""
REFERENCES = {
    "remove-prelaunch-compatibility": {
        "pipeline.py": (
            "def load_records(payload):\n"
            '    return sorted(payload["records"], key=lambda r: r["id"])\n'
        ),
        "example.py": (
            "from pipeline import load_records\n"
            'print(load_records({"records": [{"id": 2}, {"id": 1}]}))\n'
        ),
    },
    "preserve-deployed-contract": {
        "pipeline.py": (
            "def load_records(payload):\n"
            '    rows = payload["rows"] if "rows" in payload else payload["records"]\n'
            '    return sorted(rows, key=lambda r: r["id"])\n'
        ),
    },
    "reproduce-order-total": {
        "ledger.py": (
            "def total_cents(lines):\n"
            '    return sum(r["unit_cents"] * r["quantity"] for r in lines)\n'
        ),
    },
    "edit-report-preserve-uncertainty": {
        "report.md": (
            "We tested 18 fixtures: 17 parsed successfully; one had a malformed header. "
            "Production traffic is untested. Reduced manual cleanup is possible but unproven. "
            "Test a representative production sample before deciding "
            "whether to replace the parser.\n"
        ),
    },
    "repeatable-local-bootstrap": {
        "setup.py": """import argparse, json
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument("--root", type=Path, required=True)
p.add_argument("--port", type=int, required=True)
p.add_argument("--label", required=True)
a = p.parse_args()
a.root.mkdir(parents=True, exist_ok=True)
(a.root / "agent.json").write_text(json.dumps({"port": a.port, "label": a.label}))
""",
        "README.md": "Run `python3 setup.py --root DIR --port N --label LABEL`.\n",
    },
    "retain-prelaunch-policy-after-compaction": {
        "pipeline.py": RANKING,
        "README.md": (
            "Input and output objects contain `items`. "
            "Run `python3 pipeline.py INPUT OUTPUT --min-score N --limit N`.\n"
        ),
    },
}


def stage(path, files):
    for name, content in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


def results(scenario, path):
    return [
        subprocess.run(c.command, cwd=path, capture_output=True, text=True, timeout=10)
        for c in scenario.checks
    ]


def test_suite_coverage():
    assert len(SCENARIOS) == len({s.id for s in SCENARIOS})
    assert {s.kind for s in SCENARIOS} == {"checkpoint", "episode", "compaction"}
    assert any(s.held_out for s in SCENARIOS)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)
def test_reference_outcomes_pass(scenario, tmp_path):
    stage(tmp_path, scenario.files)
    stage(tmp_path, REFERENCES[scenario.id])
    for check, result in zip(scenario.checks, results(scenario, tmp_path), strict=True):
        assert result.returncode == check.expected_exit, (check.name, result.stdout, result.stderr)


@pytest.mark.parametrize(
    "case_id",
    [
        "remove-prelaunch-compatibility",
        "reproduce-order-total",
        "repeatable-local-bootstrap",
        "retain-prelaunch-policy-after-compaction",
    ],
)
def test_incomplete_starting_states_fail(case_id, tmp_path):
    scenario = next(s for s in SCENARIOS if s.id == case_id)
    stage(tmp_path, scenario.files)
    assert any(
        r.returncode != c.expected_exit
        for c, r in zip(scenario.checks, results(scenario, tmp_path), strict=True)
    )


def test_deleting_real_compatibility_fails(tmp_path):
    scenario = next(s for s in SCENARIOS if s.id == "preserve-deployed-contract")
    stage(tmp_path, REFERENCES["remove-prelaunch-compatibility"])
    assert results(scenario, tmp_path)[0].returncode != 0


def test_public_cases_exclude_private_identifiers():
    for path in CASES.glob("*.json"):
        raw = path.read_text()
        assert not any(s in raw for s in ["/Users/", "@gmail.com", "sk-or-", "rollout-2026"])


def test_semantically_equivalent_json_caller_output_passes(tmp_path):
    scenario = next(s for s in SCENARIOS if s.id == "remove-prelaunch-compatibility")
    stage(tmp_path, scenario.files)
    stage(tmp_path, REFERENCES[scenario.id])
    (tmp_path / "example.py").write_text(
        "import json\nfrom pipeline import load_records\n"
        'print(json.dumps(load_records({"records":[{"id":2},{"id":1}]})))\n'
    )
    for check, outcome in zip(scenario.checks, results(scenario, tmp_path), strict=True):
        assert outcome.returncode == check.expected_exit, (check.name, outcome.stderr)
