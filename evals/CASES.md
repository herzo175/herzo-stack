# Conversation-derived cases

The initial suite uses sanitized reconstructions, not exact historical repo or
session replays. Raw conversation archives, local paths, account identifiers,
correction messages, and the private provenance index stay on the source machine.
The agent receives only the selected fixture files, skill resources, and current
prompt. It must not receive `rubric`, `checks`, references, or provenance notes.

| Case | Source and purpose |
| --- | --- |
| `remove-prelaunch-compatibility` | Verified user correction about keeping fallbacks and calling newly written code “legacy” before launch. Reconstructed record-format migration. |
| `preserve-deployed-contract` | Designed held-out counterexample: deployed clients require both formats. This was not a separate recovered incident. |
| `repeatable-local-bootstrap` | Verified correction that code written on a VM should have been in source control so rebuilding is repeatable. Local stdlib fixture; later turns are designed extensions. |
| `reproduce-order-total` | Designed control for the existing debugging and TDD contracts. No matching historical correction was verified in the initial mining pass. |
| `edit-report-preserve-uncertainty` | Designed control for the existing deslop contract; not a recovered conversation. |
| `retain-prelaunch-policy-after-compaction` | Designed held-out seven-turn extension of the compatibility correction, with an actual compaction action after turn five. |

The compaction case has meaningful intervening implementation tasks and later
requirements. It checks retention across an explicit native compaction; it does
**not** recreate hours of work, natural context exhaustion, or a historical
compaction boundary. Report observed compaction counts. A runtime that cannot
perform and confirm compaction must reject the case rather than pass it as an
ordinary episode.

The compatibility pair intentionally needs different decisions. Deleting an
unsupported prelaunch draft is appropriate; deleting a deployed client contract
is not. Do not optimize the skills against the held-out case during iteration.

All code checks run independently after the agent finishes. Reference outcomes in
`tests/test_cases.py` establish that the tasks are solvable. They must never be
mounted into the agent's workspace. Existing tests alone cannot grade debugging
or TDD: the judge needs ordered execution evidence of a reproduced failure and a
regression that failed before the production patch. Passing final code does not
prove those steps happened.

Prose checks only protect a few concrete facts. The judge must assess semantic
uncertainty, omitted facts, and unsupported confidence. The original report already
passes the narrow factual checks; they are not a measure of editorial improvement.
Likewise, the deployed-compatibility starting state already passes its behavioral
check. Its rubric determines whether cleanup was useful without breaking clients.

## Adding cases from local histories

`tools/mine_conversations.py` scans a bounded number of bytes of explicitly named
local Codex or Claude JSONL files. It accepts actual user-message event shapes,
rejects tool outputs and obvious injected instruction blocks, and writes candidate
positions/hashes/tags without conversation text. Inspect candidate messages and
their surrounding turns locally before deciding whether they really are
corrections. Keyword matches alone are not labels.

For each accepted source, keep a private source pointer and message hash. Build a
small public reproduction with generic names and fictitious data. Mark designed
extensions and negative controls explicitly. Verify a known good outcome passes
and a relevant known bad outcome fails. Preserve constraints available before the
mistake; do not reveal the later user correction as an instruction unless the
case explicitly tests remembering feedback.

Scripted follow-ups must still make sense after different reasonable earlier
implementations. Prefer new requirements that apply to the shared interface;
avoid replaying historical complaints that assume an exact earlier answer.
