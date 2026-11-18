"""Validate reconstructed Factory mechanisms against good and meaningfully broken outcomes."""

import json
import subprocess
from pathlib import Path

import pytest

from herzo_evals.models import Scenario

ROOT = Path(__file__).parents[1]
SCENARIOS = [
    Scenario.model_validate_json(p.read_text())
    for p in sorted((ROOT / "cases").glob("factory-*.json"))
]

REFERENCES = {
    "factory-listing-count-discrepancy": {
        "importer.py": "import hashlib,json\n"
        "\n"
        "def load_release(index, body):\n"
        "    if hashlib.sha256(body).hexdigest() "
        "!= index['sha256']:\n"
        "        raise "
        "ValueError('payload_checksum_mismatch')\n"
        "    rows=json.loads(body)\n"
        "    if not isinstance(rows,list) or "
        "any(not isinstance(r,dict) or "
        "type(r.get('id')) is not int for r in "
        "rows):\n"
        "        raise "
        "ValueError('invalid_rows')\n"
        "    return "
        "{'rows':rows,'audit':{'advertised':index['advertised_count'],'actual':len(rows),'count_difference':len(rows)-index['advertised_count']}}\n"
    },
    "factory-retain-additive-fields": {
        "records.py": "def parse_records(rows):\n"
        "    out=[]\n"
        "    for row in rows:\n"
        "        if not isinstance(row,dict) or "
        "type(row.get('id')) is not int or not "
        "isinstance(row.get('name'),str):\n"
        "            raise "
        "ValueError('invalid_required_field')\n"
        "        out.append(dict(row))\n"
        "    return out\n"
    },
    "factory-nan-aware-ordered-parity": {
        "paths.py": "import math,struct\n"
        "\n"
        "def verify_paths(expected, actual):\n"
        "    if len(expected)!=len(actual):raise "
        "ValueError('coordinates_changed')\n"
        "    for left,right in "
        "zip(expected,actual):\n"
        "        if len(left)!=len(right):raise "
        "ValueError('coordinates_changed')\n"
        "        for a,b in zip(left,right):\n"
        "            if len(a)!=len(b):raise "
        "ValueError('coordinates_changed')\n"
        "            for x,y in zip(a,b):\n"
        "                if x!=y and not "
        "(isinstance(x,float) and "
        "isinstance(y,float) and math.isnan(x) and "
        "math.isnan(y)):\n"
        "                    raise "
        "ValueError('coordinates_changed')\n"
        "\n"
        "def roundtrip_paths(paths):\n"
        "    "
        "source=[[(float(x),float(y),float('nan') if "
        "m is None else float(m)) for x,y,m in path] "
        "for path in paths]\n"
        "    "
        "decoded=[[struct.unpack('<ddd',struct.pack('<ddd',*p)) "
        "for p in path] for path in source]\n"
        "    verify_paths(source,decoded)\n"
        "    return decoded\n"
    },
    "factory-preserve-wire-variant": {
        "writer.py": "import struct\n"
        "\n"
        "def encode_point(x,y,z):\n"
        "    return "
        "struct.pack('<BIddd',1,1001,x,y,z)\n"
    },
    "factory-preserve-refusal-contract": {
        "adapter.py": "from shared_parser import parse\n"
        "\n"
        "def parse_record(payload):\n"
        "    children=payload.get('children',[])\n"
        "    if not "
        "isinstance(children,list):raise "
        "ValueError('CHILDREN_INVALID')\n"
        "    if not payload.get('parent'):\n"
        "        raise ValueError('ORPHAN_CHILD' "
        "if children else 'PARENT_MISSING')\n"
        "    return parse(payload)\n"
    },
    "factory-attribute-invalid-text": {
        "text_storage.py": "class SourceTextError(ValueError):\n"
        "    def "
        "__init__(self,item_id,field,raw):\n"
        "        "
        "self.item_id,self.field,self.raw=item_id,field,raw\n"
        "        "
        "super().__init__(f'{item_id}:{field}:text_unencodable')\n"
        "\n"
        "def write_text(item_id,field,body):\n"
        "    try:return "
        "body.decode('utf-8').encode('utf-8')\n"
        "    except UnicodeError as e:raise "
        "SourceTextError(item_id,field,body) "
        "from e\n"
    },
    "factory-test-derived-json-rule": {
        "rules.py": "from rule_engine import extract\n"
        "\n"
        "def build_tags(payload):\n"
        "    return "
        "{'title':extract(payload,'title'),'organization':extract(payload,'organizations',1,'name')}\n"
    },
    "factory-exercise-framework-entrypoint": {
        "schedule.py": "from framework import Request,Skip\n"
        "\n"
        "def tick(enabled=True):\n"
        "    if not enabled:\n"
        "        yield Skip('disabled')\n"
        "        return\n"
        "    yield Request('north-daily')\n"
        "    yield Request('south-daily')\n",
        "test_helper.py": "import unittest\n"
        "from framework import "
        "evaluate_tick\n"
        "from schedule import tick\n"
        "class "
        "TestHelper(unittest.TestCase):\n"
        "    def test_requests(self):\n"
        "        "
        "self.assertEqual(evaluate_tick(tick,True)['requests'],['north-daily','south-daily'])\n"
        "    def test_skip(self):\n"
        "        "
        "self.assertEqual(evaluate_tick(tick,False)['skip'],'disabled')\n",
    },
    "factory-find-actual-executor-setting": {
        "release.py": "from copy import deepcopy\n"
        "\n"
        "def promote(config):\n"
        "    result=deepcopy(config)\n"
        "    result['server']['READY']='true'\n"
        "    return result\n"
    },
    "factory-independent-completeness-witness": {
        "capture.py": "def "
        "verify_capture(source,result):\n"
        "    if result['rows']!=source or "
        "result['feature_count']!=len(result['rows']) "
        "or "
        "result['source_count']!=len(source):\n"
        "        raise "
        "ValueError('incomplete')\n"
        "\n"
        "def collect(source):\n"
        "    rows=[dict(r) for r in "
        "source]\n"
        "    "
        "result={'rows':rows,'feature_count':len(rows),'source_count':len(source)}\n"
        "    "
        "verify_capture(source,result)\n"
        "    return result\n"
    },
    "factory-hash-actual-evidence-bytes": {
        "evidence.py": "import hashlib,json\n"
        "from pathlib import Path\n"
        "\n"
        "def build_receipts(directory):\n"
        "    result={}\n"
        "    for p in "
        "sorted(Path(directory).glob('*.txt')):\n"
        "        body=p.read_bytes()\n"
        "        "
        "result[p.name]={'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}\n"
        "    return result\n"
        "\n"
        "if __name__=='__main__':\n"
        "    "
        "Path('receipts.json').write_text(json.dumps(build_receipts('bodies'),indent=2)+'\\n')\n",
        "receipts.json": "{\n"
        '  "a.txt": {\n'
        '    "bytes": 21,\n'
        '    "sha256": '
        '"96d57d48a03d54205861976d5110ca89bc3dd90d1d9afeb0843d8641153b2748"\n'
        "  },\n"
        '  "b.txt": {\n'
        '    "bytes": 25,\n'
        '    "sha256": '
        '"d5fac508f2e3a49a1df2776674d328f75f1203f071d2591ee8ff2d57457b14b1"\n'
        "  }\n"
        "}\n",
    },
    "factory-propagate-failing-check-exit": {
        "validate.sh": "#!/bin/sh\n"
        'python3 check.py "$@"\n'
        "status=$?\n"
        "echo 'validation finished'\n"
        'exit "$status"\n'
    },
}


# Complete the reference documentation as well as the executable change.
REFERENCES["factory-attribute-invalid-text"]["README.md"] = (
    "write_text returns identical bytes for valid UTF-8. Invalid bytes raise SourceTextError "
    "with item_id, field, and raw source bytes. Strict string storage does not retain arbitrary "
    "invalid bytes as text; the attributed error preserves them for diagnostics.\n"
)
REFERENCES["factory-find-actual-executor-setting"]["README.md"] = (
    "Collection callbacks execute in server.execute with server_env, so promote sets the server "
    "READY gate. The coordinator READY gate controls a separate task and stays unchanged. "
    "promote returns a copy without mutating its input.\n"
)


def stage(root, files):
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run_checks(scenario, root):
    return [
        subprocess.run(check.command, cwd=root, capture_output=True, text=True, timeout=10)
        for check in scenario.checks
    ]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario.id)
def test_reference_outcome_passes(scenario, tmp_path):
    stage(tmp_path, scenario.files)
    stage(tmp_path, REFERENCES[scenario.id])
    for check, result in zip(scenario.checks, run_checks(scenario, tmp_path), strict=True):
        assert result.returncode == check.expected_exit, (check.name, result.stdout, result.stderr)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario.id)
def test_meaningfully_broken_outcome_fails(scenario, tmp_path):
    stage(tmp_path, scenario.files)
    outcomes = run_checks(scenario, tmp_path)
    assert any(
        result.returncode != check.expected_exit
        for check, result in zip(scenario.checks, outcomes, strict=True)
    )


def test_catalogue_matches_cases_and_sources():
    catalogue = json.loads((ROOT / "corpus/factory.json").read_text())
    assert len(catalogue) == 12
    assert {row["case_id"] for row in catalogue} == {case.id for case in SCENARIOS}
    for row in catalogue:
        case = next(case for case in SCENARIOS if case.id == row["case_id"])
        assert row["skills"] == case.skills
        assert row["held_out"] == case.held_out
        assert row["source_ids"] and row["origin"] == "incident_reconstruction"
    assert sum(case.held_out for case in SCENARIOS) == 3
    assert any(case.kind == "episode" for case in SCENARIOS)


def test_public_cases_and_catalogue_have_no_private_source_identifiers():
    paths = list((ROOT / "cases").glob("factory-*.json")) + [ROOT / "corpus/factory.json"]
    for path in paths:
        text = path.read_text()
        assert not any(
            value in text
            for value in ["/Users/", "/private/tmp/", "sk-or-", "worker_id", "run_id", "@gmail.com"]
        )
