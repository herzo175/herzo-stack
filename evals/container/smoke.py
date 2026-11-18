"""Keyless native startup/discovery smoke check, run inside the built image."""

import importlib.util
import json
import os
import subprocess
from pathlib import Path

spec = importlib.util.spec_from_file_location("driver", "/opt/herzo-evals/driver.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)

skill = Path("/tmp/smoke-skill")
skill.mkdir()
(skill / "SKILL.md").write_text(
    "---\nname: smoke\ndescription: A skill used only to check discovery.\n---\n"
    "Report a measured result.\n"
)

payload = {
    "model": "anthropic/claude-sonnet-4.5",
    "max_output_tokens": 512,
    "skills": ["smoke"],
    "prompts": [],
    "compact_after_turn": None,
}
# No prompts are sent: these commands exercise native resource discovery without inference.
assert not os.environ.get("OPENROUTER_API_KEY"), "Smoke check must run without a credential"
pi_command = [
    "pi",
    "--mode",
    "rpc",
    "--no-session",
    "--provider",
    "openrouter",
    "--model",
    payload["model"],
    "--no-skills",
    "--skill",
    str(skill),
    "--no-extensions",
    "--no-prompt-templates",
    "--no-themes",
]
driver.pi(payload, pi_command)

# For OpenCode's normal path, place the expected native skill link target in /skills via tmpfs.
skills_root = Path("/skills")
(skills_root / "smoke").symlink_to(skill, target_is_directory=True)
driver.opencode(payload)
print("Native Pi RPC and OpenCode skill discovery passed without model calls")

# Codex's app-server lists the exact same native skills as exec, without inference.
codex_home = driver.native_home(payload, "Codex")
codex_env = {**os.environ, "CODEX_HOME": str(codex_home)}
driver.codex_inventory(payload["skills"], codex_env)

# Claude emits a native init inventory before rejecting missing credentials. This deliberately
# sends no authenticated request and proves discovery/CLI compatibility, not model execution.
claude_home = driver.native_home(payload, "Claude Code")
claude_env = {
    **os.environ,
    "CLAUDE_CONFIG_DIR": str(claude_home),
    "ANTHROPIC_API_KEY": "",
    "ANTHROPIC_AUTH_TOKEN": "",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
}
startup = subprocess.run(
    [
        "claude",
        "--print",
        "--output-format",
        "stream-json",
        "--verbose",
        "--setting-sources",
        "user",
        "--settings",
        '{"disableBundledSkills":true}',
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--",
        "Report startup readiness.",
    ],
    env=claude_env,
    stdout=subprocess.PIPE,
    text=True,
    timeout=45,
)
records = [json.loads(line) for line in startup.stdout.splitlines()]
initial = next(r for r in records if r.get("type") == "system" and r.get("subtype") == "init")
assert "smoke" in initial["skills"], initial
assert startup.returncode != 0
assert any(r.get("is_error") for r in records if r.get("type") == "result")
print("Native Codex and Claude Code skill discovery passed without authenticated model calls")
