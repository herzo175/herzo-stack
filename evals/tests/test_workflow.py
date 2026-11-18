"""Execute the workflow's shell entry points against a recording CLI."""

import json
import os
import re
import subprocess

import pytest

from herzo_evals.cli import REPO, parser
from herzo_evals.models import DEFAULT_JUDGE_MODEL, Scenario, Settings
from herzo_evals.runner import load_scenarios
from herzo_evals.selection import shard_cases

WORKFLOW = REPO / ".github/workflows/evals.yml"


def run_step(name):
    text = WORKFLOW.read_text()
    step = text.split(f"      - name: {name}\n", 1)[1]
    lines = step.split("        run: |\n", 1)[1].splitlines()
    result = []
    for line in lines:
        if line and not line.startswith("          "):
            break
        result.append(line[10:])
    return "\n".join(result)


def test_dispatch_has_harness_agent_and_judge_models():
    block = WORKFLOW.read_text().split("    inputs:\n", 1)[1].split("  schedule:", 1)[0]
    assert re.findall(r"^      (\w+):", block, re.MULTILINE) == ["harness", "model", "judge_model"]
    assert "options: [pi, opencode, codex, claude]" in block
    assert "inputs.harness || 'pi'" in WORKFLOW.read_text()
    assert f"inputs.judge_model || '{DEFAULT_JUDGE_MODEL}'" in WORKFLOW.read_text()


@pytest.mark.parametrize("harness", ["pi", "opencode", "codex", "claude"])
def test_dispatch_executes_same_corpus_and_skill_comparison(tmp_path, harness):
    recorder = tmp_path / "uv"
    recorder.write_text(
        "#!/usr/bin/env python3\n"
        "import json,os,sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['RECORDED']).write_text(json.dumps(sys.argv[1:]))\n"
        "print(json.dumps({'include':[{'index':0,'total':1}]}))\n"
    )
    recorder.chmod(0o755)
    recorded = tmp_path / "args.json"
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "RECORDED": str(recorded),
        "GITHUB_OUTPUT": str(tmp_path / "outputs"),
        "EVAL_RUNTIME": harness,
        "EVAL_MODEL": {
            "claude": "anthropic/claude-opus-5.5",
            "codex": "openai/gpt-6.1-terra",
        }.get(harness, "qwen/qwen3.8-27b"),
        "EVAL_JUDGE_MODEL": "provider/judge",
        "SHARD_INDEX": "0",
        "SHARD_TOTAL": "1",
    }
    selections = []
    for name in ("Select disjoint bounded shards", "Run eval trials"):
        subprocess.run(["bash", "-e", "-c", run_step(name)], env=env, check=True)
        argv = json.loads(recorded.read_text())
        args = parser().parse_args(argv[argv.index("herzo-evals") + 1 :])
        cases = load_scenarios(args.cases, args.case, args.include_held_out)
        cases = [case for case in cases if not args.kind or case.kind in args.kind]
        selections.append({case.id for case in shard_cases(cases, *args.shard)})
        assert len(cases) == 50
        assert args.repeat == 1
    assert selections[0] == selections[1]
    assert args.runtime == harness
    assert args.no_skill_baseline and not args.baseline_ref and not args.candidate_only
    assert args.model == env["EVAL_MODEL"] and args.judge_model == "provider/judge"
    Settings(runtime=harness, model=args.model, judge_model=args.judge_model, skills_root=None)


@pytest.mark.parametrize("directory", [".codex", ".claude"])
def test_fixture_cannot_inject_native_agent_config(directory):
    with pytest.raises(ValueError, match="Unsafe fixture path"):
        Scenario(
            id="inject",
            kind="checkpoint",
            skills=["measure"],
            prompts=["Do work"],
            files={f"{directory}/settings.json": "{}"},
            checks=[{"name": "check", "command": ["true"]}],
            rubric="Test agent configuration cannot be injected.",
            provenance="Control",
        )


@pytest.mark.parametrize(
    "harness,model",
    [
        ("claude", "openai/gpt-6.1-terra"),
        ("codex", "anthropic/claude-opus-5.5"),
        ("claude", "z-ai/glm-5.3"),
        ("codex", "qwen/qwen3.8-27b"),
        ("pi", "anthropic/claude-opus-5.5"),
        ("pi", "openai/gpt-6.1-terra"),
        ("opencode", "anthropic/claude-opus-5.5"),
        ("opencode", "openai/gpt-6.1-terra"),
    ],
)
def test_invalid_pairs_rejected_even_for_matrix(harness, model, monkeypatch):
    import sys

    from herzo_evals.cli import main

    monkeypatch.setattr(
        sys, "argv", ["herzo-evals", "--matrix", "--runtime", harness, "--model", model]
    )
    with pytest.raises(SystemExit, match="requires a"):
        main()
    with pytest.raises(ValueError, match="requires a"):
        Settings(runtime=harness, model=model, judge_model="provider/judge", skills_root=None)


@pytest.mark.parametrize(
    "judge",
    [
        "google/gemini-4-hydrogen",
        "openai/gpt-6-luna",
        "anthropic/claude-haiku-5.5",
        "minimax/minimax-m3.1-flash",
    ],
)
def test_judge_choices_are_separate_from_agent_choices(judge):
    block = WORKFLOW.read_text().split("      judge_model:\n", 1)[1].split("  schedule:", 1)[0]
    agents = WORKFLOW.read_text().split("      model:\n", 1)[1].split("      judge_model:", 1)[0]
    assert f"- {judge}" in block
    assert f"- {judge}" not in agents
    assert f"default: {DEFAULT_JUDGE_MODEL}" in block


def test_cli_and_settings_default_to_gemini():
    assert parser().parse_args([]).judge_model == DEFAULT_JUDGE_MODEL
    assert Settings(runtime="pi", model="qwen/qwen3.8-27b", skills_root=None).judge_model == (
        DEFAULT_JUDGE_MODEL
    )


def test_self_judging_rejected_before_matrix_and_by_settings(monkeypatch):
    import sys

    from herzo_evals.cli import main

    model = "qwen/qwen3.8-27b"
    monkeypatch.setattr(
        sys, "argv", ["herzo-evals", "--matrix", "--model", model, "--judge-model", model]
    )
    with pytest.raises(SystemExit, match="Judge model must differ"):
        main()
    with pytest.raises(ValueError, match="Judge model must differ"):
        Settings(runtime="pi", model=model, judge_model=model, skills_root=None)
