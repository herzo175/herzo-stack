import asyncio
import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from herzo_evals import runtime
from herzo_evals.models import Scenario, Settings

DRIVER = Path(__file__).parents[1] / "container" / "driver.py"
spec = importlib.util.spec_from_file_location("eval_driver", DRIVER)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


@pytest.fixture
def scenario():
    return Scenario(
        id="fixture",
        kind="episode",
        skills=["debugging"],
        prompts=["Inspect the bug", "Fix it"],
        files={"app.py": "print('before')\n"},
        checks=[{"name": "independent", "command": ["python3", "-c", "print('private check')"]}],
        rubric="Private rubric not visible to the coding agent",
        provenance="Sanitized fixture",
    )


@pytest.fixture
def settings():
    return Settings(
        runtime="pi", model="vendor/model", judge_model="vendor/judge", skills_root=None
    )


def script(tmp_path, body):
    path = tmp_path / "fake_agent.py"
    path.write_text(body)
    return [sys.executable, str(path)]


def payload(**updates):
    return {
        "model": "vendor/model",
        "max_output_tokens": 1024,
        "skills": [],
        "prompts": ["one", "two"],
        "compact_after_turn": None,
        **updates,
    }


def test_pi_completion_and_compaction(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    command = script(
        tmp_path,
        """import json,sys
for line in sys.stdin:
 r=json.loads(line)
 if r['type']=='get_commands':
  print(json.dumps({'type':'response','id':r['id'],'success':True,'data':{'commands':[]}}),flush=True)
  continue
 if r['type']=='get_messages':
  messages=([{'role':'user','content':'one'}] if r['id'].startswith('before') else
            [{'role':'compactionSummary','summary':'Summary'}])
  print(json.dumps({'type':'response','id':r['id'],'success':True,'data':{'messages':messages}}),flush=True)
  continue
 if r['type']=='prompt':
  print(json.dumps({'type':'response','id':r['id'],'success':True}),flush=True)
  print(json.dumps({'type':'message_end','message':{'role':'assistant',
   'content':[{'type':'text','text':r['message']}],'usage':{'input':5,'output':2}}}),flush=True)
  print(json.dumps({'type':'agent_end','messages':[]}),flush=True)
 else:
  print(json.dumps({'type':'compaction_end','result':{'summary':'retained'},'aborted':False}),flush=True)
  print(json.dumps({'type':'response','id':r['id'],'success':True,'data':{'summary':'retained'}}),flush=True)
""",
    )
    result = driver.pi(payload(compact_after_turn=1), command)
    assert result["final_response"] == "two"
    assert result["compactions"] == 1 and result["usage"]["input"] == 10
    configured = json.loads((tmp_path / ".pi/agent/settings.json").read_text())
    assert configured["compaction"] == {"enabled": False, "keepRecentTokens": 1024}
    events = [json.loads(x)["data"] for x in capsys.readouterr().out.splitlines()]
    assert [x["text"] for x in events if x["type"] == "user_turn"] == ["one", "two"]
    assert any(x["type"] == "compaction_validated" and x["initial_message_removed"] for x in events)
    assert any(x["type"] == "compaction_policy" and x["keepRecentTokens"] == 1024 for x in events)
    assert next(i for i, x in enumerate(events) if x["type"] == "compaction_end") < next(
        i for i, x in enumerate(events) if x.get("text") == "two"
    )


def test_pi_requires_actual_compaction_event(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    command = script(
        tmp_path,
        """import json,sys
for line in sys.stdin:
 r=json.loads(line)
 if r['type']=='get_commands':
  print(json.dumps({'type':'response','id':r['id'],'success':True,'data':{'commands':[]}}),flush=True)
  continue
 if r['type']=='get_messages':
  print(json.dumps({'type':'response','id':r['id'],'success':True,
   'data':{'messages':[{'role':'user','content':'one'}]}}),flush=True)
  continue
 print(json.dumps({'type':'response','id':r['id'],'success':True,'data':{'summary':'fake'}}),flush=True)
 if r['type']=='prompt': print(json.dumps({'type':'agent_end','messages':[]}),flush=True)
""",
    )
    with pytest.raises(driver.ProtocolError, match="without a completion event"):
        driver.pi(payload(compact_after_turn=1), command)


def test_pi_provider_error_is_not_success(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    command = script(
        tmp_path,
        """import json,sys
r=json.loads(sys.stdin.readline())
print(json.dumps({'type':'response','id':r['id'],'success':True,'data':{'commands':[]}}),flush=True)
r=json.loads(sys.stdin.readline())
print(json.dumps({'type':'response','id':r['id'],'success':True}),flush=True)
print(json.dumps({'type':'message_end','message':{'role':'assistant','stopReason':'error',
 'errorMessage':'provider refused'}}),flush=True)
""",
    )
    with pytest.raises(driver.ProtocolError, match="provider refused"):
        driver.pi(payload(), command)


def test_opencode_continues_exact_session(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    command = script(
        tmp_path,
        """import json,sys
prompt=sys.argv[-1]
if prompt=='two':
 assert '--session' in sys.argv
 assert sys.argv[sys.argv.index('--session')+1]=='ses_fixture'
print(json.dumps({'type':'text','sessionID':'ses_fixture','part':{'text':prompt}}))
print(json.dumps({'type':'step_finish','sessionID':'ses_fixture',
 'part':{'tokens':{'input':3,'output':2},'cost':0.01}}))
""",
    )
    result = driver.opencode(payload(), command)
    assert result["final_response"] == "two"
    assert result["usage"] == {"input": 6, "output": 4, "cost_usd": 0.02}
    with pytest.raises(driver.ProtocolError, match="not supported"):
        driver.opencode(payload(compact_after_turn=1))


def test_diff_includes_added_deleted_and_rejects_symlinks(tmp_path):
    (tmp_path / "new.py").write_text("created\n")
    diff = runtime.workspace_diff({"old.py": "removed\n"}, tmp_path, 1000)
    assert "+created" in diff and "-removed" in diff
    (tmp_path / "outside").symlink_to("/etc/passwd")
    with pytest.raises(runtime.RuntimeFailure, match="Symlink"):
        runtime.workspace_diff({}, tmp_path, 1000)
    (tmp_path / "outside").unlink()
    with pytest.raises(runtime.OutputLimit):
        runtime.workspace_diff({}, tmp_path, 2)


def test_staging_only_selected_regular_skill_files(tmp_path):
    source = tmp_path / "source"
    skill = source / "debugging"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("skill")
    (source / "private.txt").write_text("not selected")
    destination = tmp_path / "selected"
    assert runtime.stage_skills(source, destination, ["debugging"]) == ["debugging"]
    assert not (destination / "private.txt").exists()
    (skill / "secret").symlink_to("/etc/passwd")
    with pytest.raises(runtime.RuntimeFailure, match="regular files"):
        runtime.stage_skills(source, tmp_path / "bad", ["debugging"])


async def test_capture_bounds_output():
    with pytest.raises(runtime.OutputLimit):
        await runtime.capture(
            [sys.executable, "-c", "print('x'*10000)"], env={"PATH": os.environ["PATH"]}, limit=100
        )


async def test_cancelled_capture_reaps_process(tmp_path):
    pidfile = tmp_path / "pid"
    task = asyncio.create_task(
        runtime.capture(
            [
                sys.executable,
                "-c",
                "import os,time,pathlib; "
                f"pathlib.Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(30)",
            ],
            env={"PATH": os.environ["PATH"]},
            limit=1000,
        )
    )
    for _ in range(100):
        if pidfile.exists():
            break
        await asyncio.sleep(0.01)
    assert pidfile.exists()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    with pytest.raises(ProcessLookupError):
        os.kill(int(pidfile.read_text()), 0)


async def test_agent_cannot_see_reference_checks_or_host_secrets(
    scenario, settings, tmp_path, monkeypatch
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "private-key")
    monkeypatch.setenv("GITHUB_TOKEN", "host-secret")
    calls = []

    async def fake_capture(args, *, env, limit, stdin=None, on_stdout=None):
        calls.append((args, env, stdin))
        if args[:3] == ["docker", "rm", "--force"]:
            return 0, b"", b""
        if "-i" in args:
            request = json.loads(stdin)
            assert set(request) == {
                "runtime",
                "model",
                "max_output_tokens",
                "prompts",
                "skills",
                "compact_after_turn",
            }
            assert "Private rubric" not in stdin.decode() and "private check" not in stdin.decode()
            assert "GITHUB_TOKEN" not in env and "private-key" not in args
            result = {
                "record": "result",
                "data": {"final_response": "done", "compactions": 0, "usage": {}},
            }
            return 0, json.dumps(result).encode() + b"\n", b""
        assert "OPENROUTER_API_KEY" not in env
        assert "--network" in args and "none" in args
        return 0, b"actual independent check", b""

    monkeypatch.setattr(runtime, "capture", fake_capture)
    result = await runtime.execute(scenario, settings, tmp_path)
    assert result.status == "completed" and result.checks[0].passed
    assert len([a for a, _, _ in calls if a[:3] == ["docker", "rm", "--force"]]) == 2
    assert (tmp_path / "trial.json").is_file()


async def test_timeout_removes_container_and_preserves_partial_events(
    scenario, settings, tmp_path, monkeypatch
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "private-key")
    removed = []

    async def fake_capture(args, *, env, limit, stdin=None, on_stdout=None):
        if args[:3] == ["docker", "rm", "--force"]:
            removed.append(args[-1])
            return 0, b"", b""
        on_stdout(b'{"record":"event","data":{"type":"tool_execution_start"}}\n')
        await asyncio.sleep(30)

    monkeypatch.setattr(runtime, "capture", fake_capture)
    result = await runtime.execute(
        scenario, settings.model_copy(update={"timeout_seconds": 0.01}), tmp_path
    )
    assert result.status == "timeout" and len(removed) == 1
    assert result.events == [{"type": "tool_execution_start"}]


async def test_missing_key_never_uses_host_agent(scenario, settings, tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = await runtime.execute(scenario, settings, tmp_path)
    assert result.status == "infrastructure_error" and "OPENROUTER_API_KEY" in result.error


async def test_cleanup_failure_is_reported(monkeypatch):
    async def fake_capture(*args, **kwargs):
        return 1, b"", b"daemon unavailable"

    monkeypatch.setattr(runtime, "capture", fake_capture)
    with pytest.raises(runtime.RuntimeFailure, match="Could not confirm sandbox cleanup"):
        await runtime.remove_container("test-container")


def test_driver_seeds_git_before_agent_runs(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("print('fixture')\n")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"runtime": "pi"})))

    def fake_pi(payload):
        commit = subprocess.check_output(["git", "log", "-1", "--format=%s"], text=True)
        assert commit.strip() == "Fixture starting state"
        assert subprocess.check_output(["git", "status", "--porcelain"], text=True) == ""
        assert subprocess.check_output(["git", "config", "user.email"], text=True).strip() == (
            "eval@example.invalid"
        )
        return {"final_response": "started after seed"}

    monkeypatch.setattr(driver, "pi", fake_pi)
    driver.main()
    assert "started after seed" in capsys.readouterr().out


@pytest.mark.parametrize("invalid_context", ["retained", "no-summary"])
def test_compaction_rejects_success_without_discarding_original_context(
    tmp_path, monkeypatch, invalid_context
):
    monkeypatch.setenv("HOME", str(tmp_path))
    command = script(
        tmp_path,
        """import json,sys
compacted=False
for line in sys.stdin:
 r=json.loads(line)
 data={}
 if r['type']=='get_commands': data={'commands':[]}
 elif r['type']=='get_messages':
  messages=[{'role':'user','content':'one'}]
  if compacted and INVALID=='retained':
   messages.insert(0,{'role':'compactionSummary','summary':'Summary'})
  elif compacted: messages=[]
  data={'messages':messages}
 elif r['type']=='compact':
  compacted=True
  data={'summary':'Summary'}
  print(json.dumps({'type':'compaction_end','result':data,'aborted':False}),flush=True)
 print(json.dumps({'type':'response','id':r['id'],'success':True,'data':data}),flush=True)
 if r['type']=='prompt': print(json.dumps({'type':'agent_end','messages':[]}),flush=True)
""".replace("INVALID", repr(invalid_context)),
    )
    with pytest.raises(driver.ProtocolError, match="Compaction did not replace"):
        driver.pi(payload(compact_after_turn=1), command)
