"""Public coverage metadata; private conversation pointers never enter this catalogue."""

import json
from collections import Counter
from pathlib import Path

from herzo_evals.models import CorpusEntry, Scenario


def load_catalogue(directory: Path, cases: list[Scenario]) -> dict[str, CorpusEntry]:
    entries = {}
    for path in sorted(directory.glob("*.json")):
        for value in json.loads(path.read_text()):
            entry = CorpusEntry.model_validate(value)
            if entry.case_id in entries:
                raise ValueError(f"Duplicate catalogue ID: {entry.case_id}")
            entries[entry.case_id] = entry
    expected = {case.id for case in cases}
    if set(entries) != expected:
        raise ValueError("Catalogue must describe every case exactly once")
    for case in cases:
        entry = entries[case.id]
        if set(entry.skills) != set(case.skills) or entry.held_out != case.held_out:
            raise ValueError(f"Catalogue does not match scenario: {case.id}")
    return entries


def coverage(cases: list[Scenario], entries: dict[str, CorpusEntry]) -> dict:
    return {
        "cases": len(cases),
        "held_out": sum(case.held_out for case in cases),
        "kinds": dict(Counter(case.kind for case in cases)),
        "origins": dict(Counter(entry.origin for entry in entries.values())),
        "scopes": dict(Counter(entry.scope for entry in entries.values())),
        "skills": dict(Counter(skill for case in cases for skill in case.skills)),
    }
