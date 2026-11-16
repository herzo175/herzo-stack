---
name: execute-plan
description: Carry out a written plan task by task, checking each step and recording decisions. Use this whenever you have a plan (from plan or the user) and are about to implement it, so work proceeds without stopping to ask between tasks.
---

# Execute a plan

Carry out the plan exactly, prove each step and keep a record that survives a
compacted context.

## Setup

- Work on a branch, or in a separate `git worktree` if other work is in
  progress in the same checkout.
- Keep a ledger next to the plan: one line per finished task with its commit and
  check result, and one line per decision you made that the plan didn't
  (`Ruling: <decision>. Why: <reason>. If wrong: <cost>`).

## Per task

1. Re-read the task and its checks.
2. Do the steps in order. Don't start the next task until this one's checks pass.
3. Commit with a message that names the task.
4. Update the ledger and tick the plan's checkboxes.

For a long plan with independent tasks, you can give each task to a fresh
subagent with the task text, the relevant files and the checks, then review its
diff against the task before moving on. Parallel subagents need separate
worktrees.

## Keep going

Don't stop to ask "should I continue?" between tasks. Decide ambiguities and
record them as rulings. Stop and ask only for: an irreversible or destructive
step, a security-sensitive action, an outward-facing side effect (a push to a
shared branch, a merge, a publish), or a plan so broken that every path forward
is a guess.

## Finish

Run the full test suite, then get one fresh-context review of the whole branch
against the plan (`second-opinion`). Report what was done, the rulings and what
remains.

Adapted from obra/superpowers (skills/executing-plans, skills/subagent-driven-development) and cursor/plugins (pstack/skills/principle-sequence-verifiable-units) (MIT; see UPSTREAM_LICENSE).
