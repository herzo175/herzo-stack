"""Designed controls have independent verifiable good and bad outcomes."""

import json
import subprocess
from pathlib import Path

import pytest

from herzo_evals.models import CorpusEntry, Scenario

ROOT = Path(__file__).parents[1]
SCENARIOS = {
    path.stem: Scenario.model_validate_json(path.read_text())
    for path in sorted((ROOT / "cases").glob("control-*.json"))
}


def stage(directory, files):
    for name, content in files.items():
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


def checks(scenario, directory):
    return [
        subprocess.run(c.command, cwd=directory, capture_output=True, text=True, timeout=10)
        for c in scenario.checks
    ]


def assert_passes(scenario, directory):
    for check, result in zip(scenario.checks, checks(scenario, directory), strict=True):
        assert result.returncode == check.expected_exit, (check.name, result.stdout, result.stderr)


def test_catalogue_has_honest_origin_and_coverage():
    raw = json.loads((ROOT / "corpus" / "controls.json").read_text())
    entries = [CorpusEntry.model_validate(item) for item in raw]
    assert {e.case_id for e in entries} == set(SCENARIOS)
    assert {s for e in entries for s in e.skills} == {"grill", "prototype", "to-tickets"}
    assert all(e.origin == "designed_control" and not e.source_ids for e in entries)
    assert sum(e.held_out for e in entries) == 1
    for entry in entries:
        scenario = SCENARIOS[entry.case_id]
        assert scenario.skills == entry.skills and scenario.held_out == entry.held_out


def test_grill_questions_and_unchanged_production(tmp_path):
    scenario = SCENARIOS["control-grill-failure-alerts"]
    stage(tmp_path, scenario.files)
    stage(
        tmp_path,
        {
            "questions.md": (
                "1. Which delivery channel should the operator use? "
                "Recommended: start with one team "
                "chat channel, because it keeps alerts together.\n"
                "2. Should transient failures alert immediately? "
                "Recommended: alert after retries are "
                "exhausted, because brief failures otherwise create noise.\n"
            )
        },
    )
    assert_passes(scenario, tmp_path)
    (tmp_path / "app.py").write_text("raise RuntimeError('Unapproved alert implementation')\n")
    assert any(r.returncode != 0 for r in checks(scenario, tmp_path))


PROTOTYPE = """<!doctype html><html><head><title>Throwaway retry choice</title></head>
<body><h1>Inline or modal confirmation?</h1>
<select id="variant">
<option value="inline">Inline</option><option value="modal">Modal</option></select>
<section id="inline"><p>Failed import</p><button onclick="showInline()">Retry</button>
<span id="confirm" hidden>Retry this import?
<button onclick="finish('Queued')">Confirm retry</button>
<button onclick="finish('Cancelled')">Cancel</button></span></section>
<section id="modal" hidden><p>Failed import</p><button onclick="showModal()">Retry</button>
<dialog id="dialog">Retry this import?
<button onclick="finish('Queued')">Confirm retry</button>
<button onclick="finish('Cancelled')">Cancel</button></dialog></section>
<p id="status">Failed</p>
<script>
const byId = id => document.getElementById(id);
byId('variant').addEventListener('change', event => {
  byId('inline').hidden = event.target.value !== 'inline';
  byId('modal').hidden = event.target.value !== 'modal';
  byId('confirm').hidden = true;
  byId('dialog').close();
  byId('status').textContent = 'Failed';
});
function showInline() { byId('confirm').hidden = false; }
function showModal() { byId('dialog').showModal(); }
function finish(state) {
  byId('status').textContent = state;
  byId('confirm').hidden = true;
  byId('dialog').close();
}
</script></body></html>
"""


def test_prototype_controls_and_unchanged_backend(tmp_path):
    scenario = SCENARIOS["control-prototype-retry-confirmation"]
    stage(tmp_path, scenario.files)
    target = "prototypes/throwaway-retry.html"
    stage(tmp_path, {target: PROTOTYPE})
    assert_passes(scenario, tmp_path)
    stage(
        tmp_path, {target: "<html><button disabled>Retry</button><p>Modal coming soon</p></html>"}
    )
    assert any(r.returncode != 0 for r in checks(scenario, tmp_path))


def publish(directory, title, body, blockers=()):
    draft = directory / f"draft-{len(list(directory.glob('draft-*')))}.md"
    draft.write_text(body)
    command = [
        "python3",
        "tracker.py",
        "create",
        "--title",
        title,
        "--body-file",
        str(draft),
        "--parent",
        "100",
    ]
    if blockers:
        command += ["--blocked-by", *map(str, blockers)]
    result = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["id"]


def prepare_tracker(directory):
    scenario = SCENARIOS["control-tickets-import-lifecycle"]
    stage(directory, scenario.files)
    registration = publish(
        directory,
        "Register a source",
        (
            "The operator can register a stable source id and URL through a command. "
            "Include persistent storage and validation. Acceptance: a valid source can be listed, "
            "duplicate ids and invalid URLs are rejected, with unit and CLI tests."
        ),
    )
    runs = publish(
        directory,
        "Run imports and inspect results",
        (
            "The operator can start an import for an existing source "
            "and inspect status and errors. "
            "Include persistence, execution boundary and CLI. Acceptance: test queued, running, "
            "success and failure from a registered source, and reject nonexistent source ids."
        ),
        [registration],
    )
    publish(
        directory,
        "Retry failed imports",
        (
            "The operator can retry a failed run from the command line "
            "while retaining the same source. "
            "Acceptance: a failed run can be retried and its result inspected; "
            "storage and CLI tests "
            "prove that source records are not duplicated."
        ),
        [runs],
    )
    return scenario


def test_native_ticket_creation_passes(tmp_path):
    scenario = prepare_tracker(tmp_path)
    assert_passes(scenario, tmp_path)


@pytest.mark.parametrize(
    "bad_mutation", ["invent-blocker", "change-parent", "erase-audit", "rewrite-tool"]
)
def test_native_ticket_grader_rejects_bad_outcomes(tmp_path, bad_mutation):
    scenario = prepare_tracker(tmp_path)
    state_path = tmp_path / ".tracker/issues.json"
    state = json.loads(state_path.read_text())
    if bad_mutation == "invent-blocker":
        state["issues"][-1]["blocked_by"] = [999]
        state_path.write_text(json.dumps(state))
    elif bad_mutation == "change-parent":
        state["issues"][0]["status"] = "closed"
        state_path.write_text(json.dumps(state))
    elif bad_mutation == "erase-audit":
        (tmp_path / ".tracker/audit.jsonl").write_text("")
    else:
        (tmp_path / "tracker.py").write_text("# modified tool\n")
    assert any(result.returncode != 0 for result in checks(scenario, tmp_path))
