---
name: second-opinion
description: "Get a fresh-context reviewer to try to break a decision, change or claim before it stands. Use this before committing to anything hard to undo (a migration, deploy, public interface or architectural choice) and whenever the user asks to challenge, stress-test or double-check something."
---

# Second opinion

A confident answer is not a correct one, and a long session turns assumptions
into "facts". Get a reviewer who doesn't share your context.

Use it for decisions that cross a module boundary, assert a consequential
property not established by existing checks (safe, idempotent, ordered, scales),
depend on context a reader can't see,
or are hard to undo (a migration, a deploy, a public interface). Skip it for
mechanical edits and clear instructions.

1. **State the claim** in one or two sentences: what you decided and why it
   matters.
2. **Extract the artifact**: the diff, plan or design, and the requirements it
   must meet. Leave out your reasoning so the reviewer can't inherit it.
   Keep reviews read-only; writable repros need isolated copies containing the
   exact reviewed changes, including uncommitted work.
3. **Ask a fresh subagent to break it**: "Find how this fails to meet the
   requirements. For runnable behavior, prove each finding against real code
   with a failing test, repro script or command output."
   For nonexecutable designs or claims, require the exact requirement and
   artifact evidence they contradict instead of a runnable repro. For high
   stakes, use reviewers with different angles or models. If delegation is
   unavailable, report that limitation; a self-review is not fresh context.
4. **Verify** findings by re-running their commands or checking their cited
   contract and artifact evidence. Keep demonstrated failures that matter;
   distinguish unresolved risks. Merge findings with one cause.
5. **Reconcile**: fix what holds up, record why you rejected the rest, and tell
   the user what changed. Recheck material changes and verify fixes before
   declaring completion; report any unresolved blocker.

Adapted from cursor/plugins (pstack/skills/interrogate) and addyosmani/agent-skills (skills/doubt-driven-development) (MIT; see UPSTREAM_LICENSE).
