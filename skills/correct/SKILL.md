---
name: correct
description: Make a repeated mistake impossible instead of adding another rule. Use this whenever the same review finding, correction or revert has happened twice in a repository, or the user says agents keep doing something wrong.
---

# Make repeated mistakes impossible

Assume every contributor is an agent that sees only the files it opened, copies
the nearest example and takes the shortest path that passes CI. Change the
repository so a change that looks right from one file is right for the whole
repository.

## Find the mistake classes

Read recent review findings, corrections, reverts, commits and the
comments that explain workarounds. Group them into classes. A class counts once
it has happened twice. Cite the issues, PRs or runs for each.

## Fix each class at the highest level that works

1. **Architecture.** Give each piece of state one owner and each task one
   supported way. Hide internals so the wrong import fails. Replace hand-synced
   lists with one source of truth. Delete the old way and dead code an agent
   would copy.
2. **Types and checks.** Make the bad state unrepresentable. If bad code still
   passes, add a lint rule or CI check whose error names the file or function to
   use instead. If the pattern is already common, fail only when a change adds
   more.
3. **Behavior tests.** Fix or delete tests that pass when the behavior breaks, or
   fail when only internals change.
4. **Guidance last**, only for judgment calls. Nothing fails when an agent skips
   it.

## Fix and prove

Fix the most frequent classes first, one commit each. Prove each new check fails
on a real past mistake, and run the same command locally and in CI. An exception
goes on the offending line with a reason.

Report each class with its evidence, the level you chose and why a higher level
did not work.

Adapted from Lauren Tan's pstack `correct` (MIT; see UPSTREAM_LICENSE).
