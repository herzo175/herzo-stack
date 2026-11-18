import json
from pathlib import Path

import pytest

from herzo_evals.corpus import coverage, load_catalogue
from herzo_evals.models import CorpusEntry, Scenario
from herzo_evals.runner import load_scenarios

ROOT = Path(__file__).parents[1]


def test_audited_corpus_is_complete_and_covers_longer_work():
    cases = load_scenarios(ROOT / "cases", [], True)
    entries = load_catalogue(ROOT / "corpus", cases)
    report = coverage(cases, entries)
    assert report["cases"] >= 50
    assert report["held_out"] >= 10
    assert report["kinds"]["episode"] >= 8
    assert report["kinds"]["compaction"] >= 3
    assert report["origins"]["incident_reconstruction"] >= 35
    # Explicit compaction is followed by work, not only an event counted at the end.
    for case in cases:
        if case.kind == "compaction":
            assert 1 <= case.compact_after_turn < len(case.prompts)


def test_catalogue_rejects_incomplete_coverage(tmp_path):
    cases = load_scenarios(ROOT / "cases", [], True)
    with pytest.raises(ValueError, match="every case"):
        load_catalogue(tmp_path, cases)


def test_catalogue_does_not_invent_unsourced_incidents():
    value = json.loads((ROOT / "corpus/initial.json").read_text())[0]
    value.update(origin="incident_reconstruction", source_ids=[])
    with pytest.raises(ValueError, match="source alias"):
        CorpusEntry.model_validate(value)


def test_catalogue_and_cases_exclude_raw_private_data():
    for directory in ["cases", "corpus"]:
        for path in (ROOT / directory).glob("*.json"):
            text = path.read_text()
            assert not any(
                marker in text
                for marker in [
                    "/Users/",
                    "rollout-2026",
                    "sk-or-",
                    "@gmail.com",
                    "iam.gserviceaccount.com",
                ]
            ), path.name


def test_scenarios_reject_ambiguous_check_names_and_empty_turns():
    case = load_scenarios(ROOT / "cases", [], True)[0]
    for update in [{"prompts": [""]}, {"checks": [case.checks[0], case.checks[0]]}]:
        with pytest.raises(ValueError):
            Scenario.model_validate(case.model_copy(update=update).model_dump())


def test_every_pack_skill_has_an_explicit_case():
    cases = load_scenarios(ROOT / "cases", [], True)
    expected = {path.parent.name for path in (ROOT.parent / "skills").glob("*/SKILL.md")}
    assert {skill for case in cases for skill in case.skills} == expected
