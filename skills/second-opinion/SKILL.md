---
name: second-opinion
description: Get a fresh-context reviewer to try to break a decision, change or claim before it stands. Use this before committing to anything hard to undo (a migration, deploy, public interface or architectural choice) and whenever the user asks to challenge, stress-test or double-check something.
---

# Second opinion

A confident answer is not a correct one, and a long session turns assumptions
into "facts". Get a reviewer who doesn't share your context.

Use it for decisions that cross a module boundary, assert something tests can't
show (safe, idempotent, ordered, scales), depend on context a reader can't see,
or are hard to undo (a migration, a deploy, a public interface). Skip it for
mechanical edits and clear instructions.

1. **State the claim** in one or two sentences: what you decided and why it
   matters.
2. **Extract the artifact**: the diff, plan or design, and the requirements it
   must meet. Leave out your reasoning so the reviewer can't inherit it.
3. **Ask a fresh subagent to break it**: "Find how this fails to meet the
   requirements. Prove each finding with a run against the real code (a failing
   test, a repro script, command output); for a plan, probe the current code."
   For high stakes, run two or three with different angles or models.
4. **Verify** each finding by re-running its command. Keep a finding only if the
   output shows the failure and the failure matters. Merge findings with one
   cause.
5. **Reconcile**: fix what holds up, record why you rejected the rest, and tell
   the user what changed.

Adapted from cursor/plugins (pstack/skills/interrogate) and addyosmani/agent-skills (skills/doubt-driven-development) (MIT; see UPSTREAM_LICENSE).
