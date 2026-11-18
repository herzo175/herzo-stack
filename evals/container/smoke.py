"""Keyless native startup/discovery smoke check, run inside the built image."""

import importlib.util
import os
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
