"""Inside-container protocol adapters. No grader or reference output is available here.

This module uses only the standard library so the same driver runs in the pinned Node image.
The outer runner owns the whole-episode deadline and destroys the container on cancellation.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


class ProtocolError(RuntimeError):
    pass


def emit(record, data):
    print(json.dumps({"record": record, "data": data}, ensure_ascii=False), flush=True)


def read_record(process):
    line = process.stdout.readline()
    if not line:
        raise ProtocolError(f"Agent exited before completing its response ({process.poll()})")
    try:
        value = json.loads(line)
    except ValueError as exc:
        raise ProtocolError("Agent emitted non-JSON protocol output") from exc
    if not isinstance(value, dict):
        raise ProtocolError("Agent protocol record must be an object")
    return value


def response_text(message):
    content = message.get("content", [])
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content if part.get("type") == "text")


def stop(process):
    if process.poll() is None:
        if process.stdin:
            process.stdin.close()
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def pi_trace_event(event):
    """Keep observable actions once; native cumulative UI snapshots are not a transcript."""
    kind = event.get("type")
    if kind == "message_update":
        update = event.get("assistantMessageEvent", {})
        if not isinstance(update.get("delta"), str):
            return None
        return {
            "type": kind,
            "assistantMessageEvent": {
                key: update[key] for key in ("type", "contentIndex", "delta") if key in update
            },
        }
    if kind == "tool_execution_update":
        return (
            None  # The completed tool event carries the outcome, without repeated partial output.
        )
    if kind == "response":
        return {key: value for key, value in event.items() if key != "data"}
    if kind in {"agent_end", "turn_end"}:
        return {
            key: value
            for key, value in event.items()
            if key not in {"messages", "message", "toolResults"}
        }
    if kind in {"message_start", "message_end"}:
        message = event.get("message", {})
        if kind == "message_start" or message.get("role") != "assistant":
            return {
                "type": kind,
                "message": {
                    key: message[key]
                    for key in ("role", "timestamp", "toolCallId", "isError")
                    if key in message
                },
            }
        content = message.get("content", [])
        if isinstance(content, list):
            visible = []
            for part in content:
                if part.get("type") == "thinking":
                    continue  # Grade observable behavior rather than internal reasoning text.
                if part.get("type") == "toolCall":
                    # Full arguments are recorded when the tool actually starts execution.
                    visible.append(
                        {key: part[key] for key in ("type", "id", "name") if key in part}
                    )
                else:
                    visible.append(part)
            message = {**message, "content": visible}
        return {**event, "message": message}
    return event


def pi(payload, command=None):
    home = Path.home() / ".pi" / "agent"
    home.mkdir(parents=True, exist_ok=True)
    # The override caps generated tokens without changing the chosen built-in model's metadata.
    (home / "models.json").write_text(
        json.dumps(
            {
                "providers": {
                    "openrouter": {
                        "modelOverrides": {
                            payload["model"]: {"maxTokens": payload["max_output_tokens"]}
                        }
                    }
                }
            }
        )
    )
    # Disable retries so a failed attempt isn't silently replaced by a successful one.
    settings = {"retry": {"enabled": False}}
    if payload.get("compact_after_turn") is not None:
        # Force a measured retention boundary, without waiting for a context overflow.
        settings["compaction"] = {"enabled": False, "keepRecentTokens": 1024}
        emit("event", {"type": "compaction_policy", "auto": False, "keepRecentTokens": 1024})
    (home / "settings.json").write_text(json.dumps(settings))
    args = command or [
        "pi",
        "--mode",
        "rpc",
        "--no-session",
        "--provider",
        "openrouter",
        "--model",
        payload["model"],
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--no-themes",
    ]
    if command is None:
        for skill in payload["skills"]:
            args.extend(["--skill", f"/skills/{skill}"])
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    result = {
        "final_response": "",
        "compactions": 0,
        "usage": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0},
    }
    observed_compactions = 0
    try:

        def receive():
            nonlocal observed_compactions
            event = read_record(process)
            trace = pi_trace_event(event)
            if trace is not None:
                emit("event", trace)
            if event.get("type") == "message_end":
                message = event.get("message", {})
                if message.get("role") == "assistant":
                    if message.get("stopReason") in {"error", "aborted"}:
                        raise ProtocolError(message.get("errorMessage", "Agent response failed"))
                    text = response_text(message)
                    if text:
                        result["final_response"] = text
                    usage = message.get("usage", {})
                    for source, target in [
                        ("input", "input"),
                        ("output", "output"),
                        ("cacheRead", "cache_read"),
                        ("cacheWrite", "cache_write"),
                    ]:
                        result["usage"][target] += usage.get(source, 0)
                    result["usage"]["cost_usd"] += usage.get("cost", {}).get("total", 0)
            if event.get("type") == "compaction_end":
                if event.get("result") and not event.get("aborted"):
                    observed_compactions += 1
                    if payload.get("compact_after_turn") is None:
                        result["compactions"] += 1
                elif event.get("errorMessage"):
                    raise ProtocolError(event["errorMessage"])
            return event

        def send(kind, request_id, **fields):
            process.stdin.write(json.dumps({"type": kind, "id": request_id, **fields}) + "\n")
            process.stdin.flush()

        def active_messages(request_id):
            send("get_messages", request_id)
            while True:
                event = receive()
                if event.get("type") == "response" and event.get("id") == request_id:
                    messages = event.get("data", {}).get("messages")
                    if not event.get("success") or not isinstance(messages, list):
                        raise ProtocolError("Pi could not report its active model context")
                    return messages

        send("get_commands", "skill-inventory")
        while True:
            event = receive()
            if event.get("type") == "response" and event.get("id") == "skill-inventory":
                if not event.get("success"):
                    raise ProtocolError("Pi could not report its loaded skills")
                commands = event.get("data", {}).get("commands", [])
                discovered = sorted(c["name"][6:] for c in commands if c.get("source") == "skill")
                if discovered != sorted(payload["skills"]):
                    raise ProtocolError(f"Pi skill inventory mismatch: {discovered}")
                emit("event", {"type": "skill_inventory", "names": discovered})
                break
        for turn, prompt in enumerate(payload["prompts"], 1):
            emit("event", {"type": "user_turn", "turn": turn, "text": prompt})
            request_id = f"turn-{turn}"
            send("prompt", request_id, message=prompt)
            accepted = ended = False
            while not (accepted and ended):
                event = receive()
                if event.get("type") == "response" and event.get("id") == request_id:
                    if not event.get("success"):
                        raise ProtocolError(event.get("error", "Pi rejected prompt"))
                    accepted = True
                if event.get("type") == "agent_end":
                    ended = True
            if payload.get("compact_after_turn") == turn:
                original = payload["prompts"][0]
                messages_before = active_messages(f"before-compact-{turn}")
                if not any(
                    message.get("role") == "user" and response_text(message) == original
                    for message in messages_before
                ):
                    raise ProtocolError(
                        "Compaction could not locate the original initial user message"
                    )
                before = observed_compactions
                compact_id = f"compact-{turn}"
                send("compact", compact_id)
                while True:
                    event = receive()
                    if event.get("type") == "response" and event.get("id") == compact_id:
                        if not event.get("success") or not event.get("data"):
                            raise ProtocolError(
                                event.get("error", "Pi returned no compaction result")
                            )
                        break
                if observed_compactions <= before:
                    raise ProtocolError(
                        "Pi returned a compaction response without a completion event"
                    )
                messages_after = active_messages(f"after-compact-{turn}")
                summary_first = bool(messages_after) and (
                    messages_after[0].get("role") == "compactionSummary"
                )
                retained_original = any(
                    message.get("role") != "compactionSummary"
                    and original in response_text(message)
                    for message in messages_after
                )
                if not summary_first or retained_original:
                    raise ProtocolError(
                        "Compaction did not replace the original initial message in active context"
                    )
                result["compactions"] += 1
                emit(
                    "event",
                    {
                        "type": "compaction_validated",
                        "initial_message_removed": True,
                        "summary_present": True,
                        "messages_before": len(messages_before),
                        "messages_after": len(messages_after),
                        "keepRecentTokens": 1024,
                    },
                )
        return result
    finally:
        stop(process)


def opencode_inventory(inventory, selected):
    builtins = sorted(item["name"] for item in inventory if item.get("location") == "<built-in>")
    discovered = sorted(item["name"] for item in inventory if item.get("location") != "<built-in>")
    if discovered != sorted(selected):
        raise ProtocolError(f"OpenCode skill inventory mismatch: {discovered}")
    return discovered, builtins


def opencode(payload, command=None):
    if payload.get("compact_after_turn") is not None:
        raise ProtocolError("OpenCode manual compaction is not supported by this adapter")
    home = Path.home() / ".config" / "opencode"
    home.mkdir(parents=True, exist_ok=True)
    (home / "opencode.json").write_text(json.dumps({"autoupdate": False, "permission": "allow"}))
    # Native v1.19.6 request preparation clamps catalog output limits with this runtime flag.
    # Preserve the catalog's context size instead of constructing a partial replacement model.
    native_env = {
        **os.environ,
        "OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX": str(payload["max_output_tokens"]),
    }
    emit(
        "event",
        {
            "type": "output_token_policy",
            "runtime": "opencode",
            "max_output_tokens": payload["max_output_tokens"],
            "source": "OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX",
        },
    )
    skills = home / "skills"
    skills.mkdir(exist_ok=True)
    for name in payload["skills"]:
        (skills / name).symlink_to(f"/skills/{name}", target_is_directory=True)
    if command is None:
        inventory = subprocess.run(
            ["opencode", "debug", "skill", "--pure"], stdout=subprocess.PIPE, text=True, check=True
        )
        discovered, builtins = opencode_inventory(json.loads(inventory.stdout), payload["skills"])
        emit("event", {"type": "skill_inventory", "names": discovered, "builtins": builtins})
    session = None
    result = {
        "final_response": "",
        "compactions": 0,
        "usage": {"input": 0, "output": 0, "cost_usd": 0.0},
    }
    for turn, prompt in enumerate(payload["prompts"], 1):
        emit("event", {"type": "user_turn", "turn": turn, "text": prompt})
        args = (
            list(command)
            if command
            else [
                "opencode",
                "run",
                "--format",
                "json",
                "--model",
                f"openrouter/{payload['model']}",
                "--auto",
                "--pure",
            ]
        )
        if session:
            args.extend(["--session", session])
        args.extend(["--", prompt])
        process = subprocess.Popen(args, stdout=subprocess.PIPE, text=True, env=native_env)
        text = []
        try:
            while line := process.stdout.readline():
                try:
                    event = json.loads(line)
                except ValueError as exc:
                    raise ProtocolError("OpenCode emitted non-JSON protocol output") from exc
                emit("event", event)
                if not isinstance(event, dict):
                    raise ProtocolError("OpenCode protocol record must be an object")
                if event.get("type") == "error":
                    raise ProtocolError(str(event.get("error", "OpenCode failed")))
                found = event.get("sessionID")
                if found:
                    if session is not None and found != session:
                        raise ProtocolError("OpenCode switched sessions during an episode")
                    session = found
                part = event.get("part", {})
                if event.get("type") == "text":
                    text.append(part.get("text", ""))
                if event.get("type") == "step_finish":
                    usage = part.get("tokens", {})
                    result["usage"]["input"] += usage.get("input", 0)
                    result["usage"]["output"] += usage.get("output", 0)
                    result["usage"]["cost_usd"] += part.get("cost", 0)
                if part.get("type") == "compaction" and part.get("auto"):
                    result["compactions"] += 1
            if process.wait() != 0:
                raise ProtocolError(f"OpenCode exited with status {process.returncode}")
            if not session:
                raise ProtocolError("OpenCode returned no session ID")
            result["final_response"] = "".join(text)
        finally:
            stop(process)
    return result


def native_home(payload, runtime):
    """The runner supplies a fresh tmpfs HOME, never a host agent configuration."""
    if payload.get("compact_after_turn") is not None:
        raise ProtocolError(f"{runtime} manual compaction is not supported by this adapter")
    home = Path.home() / (".codex" if runtime == "Codex" else ".claude")
    home.mkdir(parents=True, exist_ok=True)
    skills = (Path.home() / ".agents" if runtime == "Codex" else home) / "skills"
    skills.mkdir(parents=True, exist_ok=True)
    for name in payload["skills"]:
        (skills / name).symlink_to(f"/skills/{name}", target_is_directory=True)
    return home


def native_result():
    return {
        "final_response": "",
        "compactions": 0,
        "usage": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0},
    }


def native_records(args, env):
    process = subprocess.Popen(args, stdout=subprocess.PIPE, text=True, env=env)
    try:
        while line := process.stdout.readline():
            try:
                event = json.loads(line)
            except ValueError as exc:
                raise ProtocolError("Native agent emitted non-JSON protocol output") from exc
            if not isinstance(event, dict):
                raise ProtocolError("Native agent protocol record must be an object")
            yield event
        if process.wait() != 0:
            raise ProtocolError(f"Native agent exited with status {process.returncode}")
    finally:
        stop(process)


def codex_inventory(selected, env, command=None):
    """Use the same native loader as exec, without sending a model request."""
    process = subprocess.Popen(
        command or ["codex", "app-server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:

        def request(request_id, method, params):
            process.stdin.write(
                json.dumps({"id": request_id, "method": method, "params": params}) + "\n"
            )
            process.stdin.flush()
            while True:
                event = read_record(process)
                if event.get("id") == request_id:
                    if "error" in event:
                        raise ProtocolError(f"Codex {method} failed: {event['error']}")
                    if not isinstance(event.get("result"), dict):
                        raise ProtocolError(f"Codex {method} returned no result")
                    return event["result"]

        request(1, "initialize", {"clientInfo": {"name": "herzo-evals", "version": "1"}})
        process.stdin.write(json.dumps({"method": "initialized", "params": {}}) + "\n")
        process.stdin.flush()
        response = request(2, "skills/list", {"cwds": [str(Path.cwd())], "forceReload": True})
        entries = response.get("data", [])
        if len(entries) != 1 or entries[0].get("errors"):
            raise ProtocolError("Codex could not report its loaded skills")
        inventory = [s for s in entries[0].get("skills", []) if s.get("enabled")]
        discovered = sorted(s["name"] for s in inventory if s.get("scope") != "system")
        builtins = sorted(s["name"] for s in inventory if s.get("scope") == "system")
        if discovered != sorted(selected):
            raise ProtocolError(f"Codex skill inventory mismatch: {discovered}")
        emit("event", {"type": "skill_inventory", "names": discovered, "builtins": builtins})
    finally:
        stop(process)


def codex(payload, command=None):
    home = native_home(payload, "Codex")
    # Native Responses API provider; unsupported upstream model routes fail explicitly.
    (home / "config.toml").write_text(
        'model_provider = "openrouter"\n'
        '[model_providers.openrouter]\nname = "OpenRouter"\n'
        'base_url = "https://openrouter.ai/api/v1"\n'
        'env_key = "OPENROUTER_API_KEY"\nwire_api = "responses"\n'
        "request_max_retries = 0\nstream_max_retries = 0\n"
    )
    env = {**os.environ, "CODEX_HOME": str(home)}
    emit(
        "event",
        {
            "type": "output_token_policy",
            "runtime": "codex",
            "requested_max_output_tokens": payload["max_output_tokens"],
            "enforced": False,
            "source": "native_provider_limits",
        },
    )
    if command is None:
        codex_inventory(payload["skills"], env)
    result = native_result()
    session = None
    for turn, prompt in enumerate(payload["prompts"], 1):
        emit("event", {"type": "user_turn", "turn": turn, "text": prompt})
        args = list(command) if command else ["codex", "exec"]
        if session:
            args.extend(["resume", session])
        args.extend(
            [
                "--json",
                "--dangerously-bypass-approvals-and-sandbox",
                "--ignore-rules",
                "--model",
                payload["model"],
                "--",
                prompt,
            ]
        )
        completed = started = False
        text = []
        for event in native_records(args, env):
            kind = event.get("type")
            # The JSONL CLI emits completed items; omit internal reasoning, keep tools/outcomes.
            if event.get("item", {}).get("type") != "reasoning":
                emit("event", event)
            if kind in {"error", "turn.failed"}:
                raise ProtocolError(
                    f"Codex failed: {event.get('error', event.get('message', event))}"
                )
            if kind == "thread.started":
                found = event.get("thread_id")
                if not found or (session is not None and found != session):
                    raise ProtocolError("Codex returned a missing or changed session ID")
                session = found
                started = True
            if kind == "turn.started":
                if completed:
                    raise ProtocolError("Codex started another turn after completion")
            if kind == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "agent_message":
                    text.append(item.get("text", ""))
                if item.get("type") == "context_compaction":
                    result["compactions"] += 1
            if kind == "turn.completed":
                if completed:
                    raise ProtocolError("Codex returned duplicate turn completion")
                completed = True
                usage = event.get("usage", {})
                result["usage"]["input"] += usage.get("input_tokens", 0)
                result["usage"]["output"] += usage.get("output_tokens", 0)
                result["usage"]["cache_read"] += usage.get("cached_input_tokens", 0)
        if not started or not completed or not any(text):
            raise ProtocolError("Codex returned no completed response in the expected session")
        result["final_response"] = "\n".join(text)
    return result


def claude_code(payload, command=None):
    home = native_home(payload, "Claude Code")
    env = {
        **os.environ,
        "CLAUDE_CONFIG_DIR": str(home),
        "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
        "ANTHROPIC_AUTH_TOKEN": os.environ.get("OPENROUTER_API_KEY", ""),
        "ANTHROPIC_API_KEY": "",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(payload["max_output_tokens"]),
    }
    emit(
        "event",
        {
            "type": "output_token_policy",
            "runtime": "claude-code",
            "max_output_tokens": payload["max_output_tokens"],
            "source": "CLAUDE_CODE_MAX_OUTPUT_TOKENS",
        },
    )
    result = native_result()
    result["usage"]["cost_usd"] = 0.0
    session = None
    for turn, prompt in enumerate(payload["prompts"], 1):
        emit("event", {"type": "user_turn", "turn": turn, "text": prompt})
        args = (
            list(command)
            if command
            else [
                "claude",
                "--print",
                "--output-format",
                "stream-json",
                "--verbose",
                "--dangerously-skip-permissions",
                "--setting-sources",
                "user",
                "--settings",
                '{"disableBundledSkills":true}',
                "--strict-mcp-config",
                "--mcp-config",
                '{"mcpServers":{}}',
                "--model",
                payload["model"],
            ]
        )
        if session:
            args.extend(["--resume", session])
        args.extend(["--", prompt])
        initialized = completed = False
        for event in native_records(args, env):
            kind = event.get("type")
            trace = event
            if kind in {"assistant", "user"}:
                message = event.get("message", {})
                content = message.get("content", [])
                if isinstance(content, list):
                    trace = {
                        **event,
                        "message": {
                            **message,
                            "content": [
                                part
                                for part in content
                                if part.get("type") not in {"thinking", "redacted_thinking"}
                            ],
                        },
                    }
            emit("event", trace)
            found = event.get("session_id")
            if found:
                if session is not None and found != session:
                    raise ProtocolError("Claude Code switched sessions during an episode")
                session = found
            if kind == "system" and event.get("subtype") == "init":
                if not found:
                    raise ProtocolError("Claude Code init returned no session ID")
                inventory = event.get("skills")
                if not isinstance(inventory, list) or not set(payload["skills"]).issubset(
                    inventory
                ):
                    raise ProtocolError("Claude Code skill inventory mismatch")
                emit(
                    "event",
                    {
                        "type": "skill_inventory",
                        "names": sorted(payload["skills"]),
                        "native_extras": sorted(set(inventory) - set(payload["skills"])),
                    },
                )
                initialized = True
            if kind == "system" and event.get("subtype") == "compact_boundary":
                result["compactions"] += 1
            if kind == "error" or event.get("is_api_error_message"):
                raise ProtocolError(f"Claude Code failed: {event.get('error', event)}")
            if kind == "result":
                if completed:
                    raise ProtocolError("Claude Code returned duplicate completion")
                if event.get("is_error") or event.get("subtype") != "success":
                    raise ProtocolError(
                        f"Claude Code failed: {event.get('errors', event.get('result', event))}"
                    )
                result["final_response"] = event.get("result", "")
                usage = event.get("usage", {})
                for source, target in [
                    ("input_tokens", "input"),
                    ("output_tokens", "output"),
                    ("cache_read_input_tokens", "cache_read"),
                    ("cache_creation_input_tokens", "cache_write"),
                ]:
                    result["usage"][target] += usage.get(source, 0)
                result["usage"]["cost_usd"] += event.get("total_cost_usd", 0)
                completed = True
        if not initialized or not completed or not result["final_response"]:
            raise ProtocolError(
                "Claude Code returned no completed response in the expected session"
            )
    return result


def main():
    payload = json.loads(sys.stdin.readline())
    os.environ["CI"] = "true"
    subprocess.run(["git", "init", "--quiet"], check=True)
    subprocess.run(["git", "config", "user.email", "eval@example.invalid"], check=True)
    subprocess.run(["git", "config", "user.name", "Skill evaluation"], check=True)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(
        ["git", "commit", "--quiet", "--allow-empty", "-m", "Fixture starting state"], check=True
    )
    adapters = {"pi": pi, "opencode": opencode, "codex": codex, "claude-code": claude_code}
    if payload["runtime"] not in adapters:
        raise ProtocolError(f"Unsupported runtime: {payload['runtime']}")
    result = adapters[payload["runtime"]](payload)
    emit("result", result)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit("error", {"message": str(exc)})
        raise SystemExit(1) from None
