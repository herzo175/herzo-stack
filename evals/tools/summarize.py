"""Write per-case outcomes to the Actions summary; full evidence stays in artifacts."""

import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
lines = ["## Skill evaluation results", "", "Behavioral verdicts are report-only.", ""]
lines += ["| Arm | Case | Execution | Checks | Behavior |", "|---|---|---|---|---|"]
for arm in ["baseline", "candidate"]:
    path = root / arm / "summary.json"
    if path.is_file():
        rows = json.loads(path.read_text())
    else:
        rows = [
            json.loads(item.read_text()) for item in sorted((root / arm).glob("*/verdict.json"))
        ]
        if not rows:
            if (root / arm).exists():
                lines.append(f"| {arm} | — | No completed case report | — | — |")
            continue
        lines.append(f"| {arm} | — | Partial run; completed cases below | — | — |")
    for row in rows:
        assertions = row.get("assertions", {})
        checks = [v["passed"] for k, v in assertions.items() if k.startswith("check_")]
        behavior = assertions.get("behavior", {}).get("passed")
        verdict = "not judged" if behavior is None else "pass" if behavior else "fail"
        lines.append(
            f"| {arm} | {row['case']} | {row['status']} | {sum(checks)}/{len(checks)} | {verdict} |"
        )
text = "\n".join(lines) + "\n"
print(text)
if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
    with Path(summary).open("a") as stream:
        stream.write(text)
