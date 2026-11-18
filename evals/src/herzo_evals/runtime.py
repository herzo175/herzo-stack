"""Run real agent episodes in disposable Docker containers, then check their work."""

import asyncio
import difflib
import hashlib
import json
import os
import shutil
import signal
import tempfile
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from herzo_evals.models import CheckResult, Scenario, Settings, TrialResult


class OutputLimit(RuntimeError):
    """A subprocess or final workspace exceeded its evidence budget."""


class RuntimeFailure(RuntimeError):
    pass


def docker_environment(*, agent: bool) -> dict[str, str]:
    """Docker's client can use its host config, but the container only receives explicit env."""
    names = ["PATH", "HOME", "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG"]
    env = {name: os.environ[name] for name in names if name in os.environ}
    if agent:
        env["OPENROUTER_API_KEY"] = os.environ["OPENROUTER_API_KEY"]
    return env


async def capture(
    args: list[str],
    *,
    env: dict[str, str],
    limit: int,
    stdin: bytes | None = None,
    on_stdout: Callable[[bytes], None] | None = None,
) -> tuple[int, bytes, bytes]:
    """Bound both pipes together; cancellation reaps the entire client process group."""
    process = await asyncio.create_subprocess_exec(
        *args,
        env=env,
        stdin=asyncio.subprocess.PIPE if stdin is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    size = 0

    async def read(stream: asyncio.StreamReader, *, stdout: bool = False) -> bytes:
        nonlocal size
        chunks = []
        while chunk := await stream.read(16384):
            size += len(chunk)
            if size > limit:
                raise OutputLimit("Subprocess output exceeded the configured byte budget")
            chunks.append(chunk)
            if stdout and on_stdout is not None:
                on_stdout(chunk)
        return b"".join(chunks)

    async def write() -> None:
        if process.stdin is not None:
            process.stdin.write(stdin or b"")
            await process.stdin.drain()
            process.stdin.close()

    tasks = [
        asyncio.create_task(read(process.stdout, stdout=True)),
        asyncio.create_task(read(process.stderr)),
        asyncio.create_task(write()),
    ]
    try:
        stdout, stderr, _ = await asyncio.gather(*tasks)
        return await process.wait(), stdout, stderr
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await process.wait()


async def remove_container(name: str) -> None:
    """A stopped Docker client alone does not stop its container."""
    try:
        code, _, stderr = await asyncio.wait_for(
            capture(
                ["docker", "rm", "--force", name],
                env=docker_environment(agent=False),
                limit=100_000,
            ),
            timeout=15,
        )
        if code and b"No such container" not in stderr:
            raise RuntimeFailure(
                "Could not confirm sandbox cleanup: " + stderr.decode(errors="replace")[-1000:]
            )
    except (OSError, TimeoutError, OutputLimit) as exc:
        raise RuntimeFailure("Could not confirm sandbox cleanup") from exc


def stage_skills(source: Path | None, destination: Path, names: list[str]) -> list[str]:
    destination.mkdir()
    if source is None:
        return []
    copied = []
    for name in names:
        root = source / name
        if root.is_symlink() or not (root / "SKILL.md").is_file():
            raise RuntimeFailure(f"Missing skill directory: {name}")
        for item in root.rglob("*"):
            if item.is_symlink() or not (item.is_dir() or item.is_file()):
                raise RuntimeFailure(f"Skill resources must be regular files: {name}")
        shutil.copytree(root, destination / name)
        for item in (destination / name).rglob("*"):
            item.chmod(0o555 if item.is_dir() else 0o444)
        (destination / name).chmod(0o555)
        copied.append(name)
    destination.chmod(0o555)
    return copied


def workspace_diff(initial: dict[str, str], workspace: Path, limit: int) -> str:
    """Compare trusted initial bytes with bounded final files, independent of the agent's Git."""
    final = {}
    size = count = 0
    pending = [workspace]
    while pending:
        folder = pending.pop()
        for item in folder.iterdir():
            relative = item.relative_to(workspace).as_posix()
            if relative.split("/", 1)[0] == ".git" or "__pycache__" in item.parts:
                continue
            count += 1
            if count > 2000:
                raise OutputLimit("Final workspace exceeded 2000 entries")
            if item.is_symlink():
                raise RuntimeFailure(f"Symlink in final workspace: {relative}")
            if item.is_dir():
                pending.append(item)
            elif item.is_file():
                size += item.stat().st_size
                if size > limit:
                    raise OutputLimit("Final workspace exceeded the configured byte budget")
                final[relative] = item.read_bytes()
            else:
                raise RuntimeFailure(f"Nonregular file in final workspace: {relative}")
    lines = []
    for name in sorted(initial.keys() | final.keys()):
        before = initial.get(name, "").encode()
        after = final.get(name, b"")
        if before == after:
            if name not in initial:
                lines.append(f"Added empty file: {name}\n")
            elif name not in final:
                lines.append(f"Removed empty file: {name}\n")
            continue
        binary = b"\0" in before or b"\0" in after
        if not binary:
            try:
                before_text, after_text = before.decode(), after.decode()
            except UnicodeDecodeError:
                binary = True
        if binary:
            action = (
                "added" if name not in initial else "removed" if name not in final else "changed"
            )
            lines.append(
                f"Binary file {name} ({action}): {len(before)} bytes "
                f"sha256:{hashlib.sha256(before).hexdigest()}"
                f" -> {len(after)} bytes sha256:{hashlib.sha256(after).hexdigest()}\n"
            )
        else:
            lines.extend(
                difflib.unified_diff(
                    before_text.splitlines(keepends=True),
                    after_text.splitlines(keepends=True),
                    fromfile=f"a/{name}",
                    tofile=f"b/{name}",
                )
            )
    diff = "".join(lines)
    if len(diff.encode()) > limit:
        raise OutputLimit("Workspace diff exceeded the configured byte budget")
    return diff


def docker_base(name: str, workspace: Path) -> list[str]:
    uid, gid = os.getuid() or 1000, os.getgid() or 1000
    return [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--init",
        "--user",
        f"{uid}:{gid}",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        "2g",
        "--cpus",
        "1",
        "--pids-limit",
        "128",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=256m,mode=1777",
        "--tmpfs",
        f"/home/node:rw,nosuid,nodev,size=256m,uid={uid},gid={gid}",
        "--mount",
        f"type=bind,src={workspace},dst=/work",
        "--workdir",
        "/work",
    ]


def parse_records(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    events = []
    result = None
    for line in data.split(b"\n"):
        if not line.strip():
            continue
        record = json.loads(line)
        if record["record"] == "event":
            events.append(record["data"])
        elif record["record"] == "error":
            raise RuntimeFailure(record["data"]["message"])
        elif record["record"] == "result":
            if result is not None:
                raise RuntimeFailure("Driver emitted multiple final results")
            result = record["data"]
        else:
            raise RuntimeFailure("Unknown driver record")
    if result is None:
        raise RuntimeFailure("Driver returned no final result")
    return events, result


async def execute(scenario: Scenario, settings: Settings, output_dir: Path) -> TrialResult:
    """Run one whole conversation. No host CLI fallback is permitted."""
    started = time.monotonic()
    result = TrialResult(status="infrastructure_error")
    if not os.environ.get("OPENROUTER_API_KEY"):
        return result.model_copy(update={"error": "OPENROUTER_API_KEY is not configured"})
    if settings.runtime == "opencode" and scenario.compact_after_turn is not None:
        return result.model_copy(
            update={"error": "OpenCode adapter does not support manual compaction"}
        )
    name = f"herzo-eval-{uuid.uuid4().hex}"
    await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="herzo-eval-") as temporary:
            root = Path(temporary)
            # Docker's unprivileged UID must traverse the staging directory on Linux runners.
            await asyncio.to_thread(root.chmod, 0o755)
            workspace = root / "work"
            workspace.mkdir(mode=0o777)
            workspace.chmod(0o777)
            for path, content in scenario.files.items():
                target = workspace / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
                target.chmod(0o666)
                for directory in target.parents:
                    if directory == root:
                        break
                    directory.chmod(0o777)
            skills = root / "skills"
            selected = stage_skills(settings.skills_root, skills, scenario.skills)
            payload = (
                json.dumps(
                    {
                        "runtime": settings.runtime,
                        "model": settings.model,
                        "max_output_tokens": settings.max_output_tokens,
                        "prompts": scenario.prompts,
                        "skills": selected,
                        "compact_after_turn": scenario.compact_after_turn,
                    }
                ).encode()
                + b"\n"
            )

            pending_output = b""

            def record_events(chunk: bytes) -> None:
                nonlocal pending_output
                pending_output += chunk
                while b"\n" in pending_output:
                    line, pending_output = pending_output.split(b"\n", 1)
                    try:
                        value = json.loads(line)
                    except ValueError:
                        continue  # The complete protocol parser reports malformed output.
                    if isinstance(value, dict) and value.get("record") == "event":
                        result.events.append(value["data"])

            async def episode() -> None:
                args = docker_base(name, workspace) + [
                    "--mount",
                    f"type=bind,src={skills},dst=/skills,readonly",
                    "--env",
                    "OPENROUTER_API_KEY",
                    "--env",
                    "HOME=/home/node",
                    "--env",
                    "CI=true",
                    "-i",
                    settings.image,
                ]
                try:
                    code, stdout, stderr = await capture(
                        args,
                        env=docker_environment(agent=True),
                        limit=settings.max_output_bytes,
                        stdin=payload,
                        on_stdout=record_events,
                    )
                finally:
                    await remove_container(name)
                if code != 0:
                    detail = stderr.decode(errors="replace")[-2000:]
                    try:
                        parse_records(stdout)
                    except RuntimeFailure as exc:
                        detail = str(exc)
                    raise RuntimeFailure(f"Agent container failed ({code}): {detail}")
                remaining = settings.max_output_bytes - len(stdout) - len(stderr)
                result.events, final = parse_records(stdout)
                result.final_response = final["final_response"]
                result.compactions = final["compactions"]
                result.usage = final["usage"]
                if scenario.kind == "compaction" and result.compactions < 1:
                    raise RuntimeFailure(
                        "Compaction scenario completed without observed compaction"
                    )
                result.diff = await asyncio.to_thread(
                    workspace_diff, scenario.files, workspace, remaining
                )
                remaining -= len(result.diff.encode())
                # Agent processes have ended before reference checks or their commands are exposed.
                for check in scenario.checks:
                    check_name = f"{name}-check"
                    try:
                        code, stdout, stderr = await capture(
                            docker_base(check_name, workspace)
                            + [
                                "--network",
                                "none",
                                "--entrypoint",
                                check.command[0],
                                settings.image,
                                *check.command[1:],
                            ],
                            env=docker_environment(agent=False),
                            limit=remaining,
                        )
                    finally:
                        await remove_container(check_name)
                    remaining -= len(stdout) + len(stderr)
                    result.checks.append(
                        CheckResult(
                            name=check.name,
                            passed=code == check.expected_exit,
                            exit_code=code,
                            output=(stdout + stderr).decode(errors="replace"),
                        )
                    )
                result.status = "completed"

            await asyncio.wait_for(episode(), timeout=settings.timeout_seconds)
    except TimeoutError:
        result.status, result.error = "timeout", "Whole-episode execution deadline exceeded"
    except OutputLimit as exc:
        result.status, result.error = "output_limit", str(exc)
    except (OSError, RuntimeFailure, ValueError, KeyError, TypeError) as exc:
        result.status, result.error = "infrastructure_error", str(exc)
    finally:
        result.duration = time.monotonic() - started
    # Redact the only credential available to the agent before persisting diagnostic evidence.
    key = os.environ.get("OPENROUTER_API_KEY", "")
    encoded = result.model_dump_json()
    if key:
        encoded = encoded.replace(key, "[REDACTED_OPENROUTER_KEY]")
    result = TrialResult.model_validate_json(encoded)
    (output_dir / "trial.json").write_text(result.model_dump_json(indent=2) + "\n")
    return result
