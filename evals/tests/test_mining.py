"""History mining must not turn tool results or transcript snippets into labels."""

import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "tools" / "mine_conversations.py"
spec = importlib.util.spec_from_file_location("mine_conversations", MODULE_PATH)
mining = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mining)


def test_only_actual_user_messages_are_candidates(tmp_path):
    text = "Why are we keeping speculative fallback paths?"
    events = [
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            },
        },
        {"type": "response_item", "payload": {"type": "function_call_output", "output": text}},
        {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "tool_result", "content": text}]},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "# AGENTS.md\n" + text}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": text}],
            },
        },
    ]
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(map(json.dumps, events)) + "\n")
    results = mining.mine([path], 100_000)
    assert len(results) == 1
    assert results[0]["tags"] == ["compatibility"]
    assert text not in json.dumps(results)
    with path.open("rb") as source:
        source.seek(results[0]["offset"])
        assert mining.user_text(json.loads(source.readline())) == text


def test_byte_limit_stops_before_complete_message(tmp_path):
    event = {"type": "user", "message": {"role": "user", "content": "Remove the legacy code"}}
    path = tmp_path / "session.jsonl"
    path.write_text(json.dumps(event) + "\n")
    assert mining.mine([path], 10) == []
