"""Protocol checks use fake executables; they make no inference-quality claim."""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "native_driver", Path(__file__).parents[1] / "container/driver.py"
)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def payload(**updates):
    return {
        "model": "openai/gpt-6.2-sol",
        "max_output_tokens": 1024,
        "skills": [],
        "prompts": ["one", "two"],
        "compact_after_turn": None,
        **updates,
    }


def fake(tmp_path, body):
    path = tmp_path / "agent.py"
    path.write_text(body)
    return [sys.executable, str(path)]


@pytest.mark.parametrize("adapter", [driver.codex, driver.claude_code])
def test_native_rejects_forced_compaction(adapter):
    with pytest.raises(driver.ProtocolError, match="manual compaction is not supported"):
        adapter(payload(compact_after_turn=1))


def test_codex_resumes_thread_and_records_tools(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    command = fake(
        tmp_path,
        """import sys,json,os
assert os.environ['CODEX_HOME'].endswith('/.codex')
if sys.argv[-1]=='two':
 assert sys.argv[1:3]==['resume','thread-fixture']
for event in [
 {'type':'thread.started','thread_id':'thread-fixture'},
 {'type':'turn.started'},
 {'type':'item.completed','item':{'type':'command_execution','command':'python3 test.py',
 'aggregated_output':'failed','exit_code':1}},
 {'type':'item.completed','item':{'type':'agent_message','text':sys.argv[-1]}},
 {'type':'turn.completed','usage':{'input_tokens':4,'output_tokens':2,'cached_input_tokens':1}}]:
 print(json.dumps(event))
""",
    )
    result = driver.codex(payload(), command)
    assert result["final_response"] == "two"
    assert result["usage"] == {"input": 8, "output": 4, "cache_read": 2, "cache_write": 0}
    trace = capsys.readouterr().out
    assert "python3 test.py" in trace and "failed" in trace
    assert (
        json.loads((tmp_path / ".codex/config.toml").read_text().splitlines()[0].split(" = ")[1])
        == "openrouter"
    )


@pytest.mark.parametrize(
    "events",
    [
        [
            {"type": "thread.started", "thread_id": "s"},
            {"type": "turn.failed", "error": {"message": "refused"}},
        ],
        [{"type": "thread.started", "thread_id": "s"}, {"type": "turn.completed"}],
        [{"type": "item.completed", "item": {"type": "agent_message", "text": "fake"}}],
        [
            [],
        ],
    ],
)
def test_codex_never_accepts_incomplete_or_failed_protocol(tmp_path, monkeypatch, events):
    monkeypatch.setenv("HOME", str(tmp_path))
    command = fake(tmp_path, f"import json\nfor e in {events!r}: print(json.dumps(e))\n")
    with pytest.raises(driver.ProtocolError):
        driver.codex(payload(prompts=["one"]), command)


def test_claude_resumes_and_checks_success_flag(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    command = fake(
        tmp_path,
        """import sys,json,os
assert os.environ['ANTHROPIC_AUTH_TOKEN']=='test-only'
assert os.environ['ANTHROPIC_API_KEY']==''
assert os.environ['ANTHROPIC_BASE_URL']=='https://openrouter.ai/api'
assert os.environ['CLAUDE_CODE_MAX_OUTPUT_TOKENS']=='1024'
if sys.argv[-1]=='two': assert sys.argv[sys.argv.index('--resume')+1]=='session-fixture'
print(json.dumps({'type':'system','subtype':'init','session_id':'session-fixture','skills':[]}))
print(json.dumps({'type':'assistant','message':{'content':[
 {'type':'thinking','thinking':'private reasoning'},
 {'type':'tool_use','name':'Bash','input':{'command':'python3 test.py'}}]}}))
print(json.dumps({'type':'result','session_id':'session-fixture','subtype':'success','is_error':False,'result':sys.argv[-1],'usage':{'input_tokens':5,'output_tokens':2},'total_cost_usd':0.01}))
""",
    )
    result = driver.claude_code(payload(), command)
    assert result["final_response"] == "two"
    assert result["usage"]["input"] == 10 and result["usage"]["cost_usd"] == 0.02
    trace = capsys.readouterr().out
    assert "python3 test.py" in trace and "private reasoning" not in trace


@pytest.mark.parametrize("failure", ["error", "missing", "session", "inventory"])
def test_claude_protocol_failures(tmp_path, monkeypatch, failure):
    monkeypatch.setenv("HOME", str(tmp_path))
    init = {"type": "system", "subtype": "init", "session_id": "s", "skills": []}
    result = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "session_id": "s",
        "result": "ok",
    }
    if failure == "error":
        result["is_error"] = True
    if failure == "session":
        result["session_id"] = "different"
    events = [init] if failure == "missing" else [init, result]
    command = fake(tmp_path, f"import json\nfor e in {events!r}: print(json.dumps(e))\n")
    with pytest.raises(driver.ProtocolError):
        driver.claude_code(
            payload(prompts=["one"], skills=["absent"] if failure == "inventory" else []), command
        )


def test_codex_inventory_is_native_and_exact(tmp_path, capsys):
    command = fake(
        tmp_path,
        """import json,sys
for line in sys.stdin:
 r=json.loads(line)
 if r.get('method')=='initialize': result={}
 elif r.get('method')=='skills/list':
  result={'data':[{'errors':[],'skills':[{'name':'selected','enabled':True,'scope':'user'},{'name':'builtin','enabled':True,'scope':'system'}]}]}
 else: continue
 print(json.dumps({'id':r['id'],'result':result}),flush=True)
""",
    )
    driver.codex_inventory(["selected"], os.environ, command)
    assert "builtin" in capsys.readouterr().out
    with pytest.raises(driver.ProtocolError, match="inventory mismatch"):
        driver.codex_inventory([], os.environ, command)
