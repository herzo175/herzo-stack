"""Index candidate corrections locally; never export conversation text.

Candidates require human review before becoming scenarios. A keyword match is not
proof that a message is a correction. Run this separately from Actions.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

PATTERNS = {
    "compatibility": r"fallback|legacy|speculativ",
    "repeatability": r"source control|repeatable|reproducible",
    "debugging": r"reproduc|before.{0,30}fix|why.{0,30}(fail|test)",
    "writing": r"uncertain|too verbose|shorter",
    "tool-choice": r"unnecessary.{0,40}(tool|automation)|just using.{0,30}cli",
}


def user_text(event):
    """Accept text from actual message events, not tool output or summaries."""
    payload = event.get("payload", {})
    if (
        event.get("type") == "response_item"
        and payload.get("type") == "message"
        and payload.get("role") == "user"
    ):
        content = payload.get("content", [])
    elif event.get("type") == "user" and event.get("message", {}).get("role") == "user":
        content = event["message"].get("content", [])
    else:
        return ""
    text = (
        content
        if isinstance(content, str)
        else "\n".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") in {"text", "input_text"}
        )
    )
    if text.lstrip().startswith(("<", "# AGENTS", "[Request interrupted")):
        return ""
    return text if 8 <= len(text) <= 2500 else ""


def mine(paths, max_bytes):
    remaining = max_bytes
    matches = []
    for path in paths:
        if remaining <= 0:
            break
        with path.open("rb") as source:
            while remaining > 0:
                offset = source.tell()
                line = source.readline(remaining + 1)
                if not line:
                    break
                if len(line) > remaining:
                    remaining = 0
                    break
                remaining -= len(line)
                try:
                    event = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    continue
                text = user_text(event)
                tags = [tag for tag, pattern in PATTERNS.items() if re.search(pattern, text, re.I)]
                if tags:
                    matches.append(
                        {
                            "path": str(path.resolve()),
                            "offset": offset,
                            "timestamp": event.get("timestamp"),
                            "tags": tags,
                            "message_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        }
                    )
    return matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="+", help="Local JSONL files")
    parser.add_argument(
        "--output", type=Path, required=True, help="Private local index destination"
    )
    parser.add_argument("--max-bytes", type=int, default=50_000_000)
    args = parser.parse_args()
    if args.max_bytes <= 0:
        parser.error("--max-bytes must be positive")
    matches = mine(args.paths, args.max_bytes)
    args.output.write_text(json.dumps(matches, indent=2) + "\n")
    args.output.chmod(0o600)
    print(f"Indexed {len(matches)} candidates; no conversation text exported")


if __name__ == "__main__":
    main()
