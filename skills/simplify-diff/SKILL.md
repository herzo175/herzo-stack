---
name: simplify-diff
description: "Clean up your own diff without changing behavior. Use this every time a change works and its tests pass, before you commit or push for review, to remove dead code, duplication, layered patches and comments that restate code."
---

# Simplify your diff before review

Make the change easier to read and review while keeping its behavior exactly the
same. Work only on what your diff touched; don't refactor unrelated code.

## Before removing anything

Know why it exists: what calls it, what edge case it handles, which test defines
it, and what `git log -L` or `git blame` says about it. If you can't answer, leave
it.

## Look for

- **Subtract first.** Dead branches, unused parameters and imports,
  commented-out code, flags nothing sets, a wrapper that only forwards a call.
- **Duplication.** A helper copied from another module (move it to a shared
  module instead), the same check in several places.
- **Patches on patches.** A guard, retry or special case added on top of an
  earlier one for the same symptom. Replace the stack with the fix at the cause.
- **Comments.** Delete comments that restate the code or narrate the change
  ("now uses X"). Keep comments that say why: a constraint, a source quirk, a
  measured limit. A deliberate shortcut with a known ceiling (a full scan, a
  global lock, a naive heuristic) gets one comment naming the ceiling and the
  upgrade path.
- **Shape.** Nesting three levels deep (use early returns), boolean flag
  parameters, names like `data`, `result` or `tmp`, and a function doing several
  jobs.

## Don't

- Inline a helper that gave a concept a name, or merge unrelated functions.
- Optimize for line count. Fewer lines is not the goal; easier reading is.
- Mix a large refactor into a feature or fix. File it as follow-up work.
- Simplify away validation of external input, error handling that prevents data
  loss, security checks, or anything the task explicitly asked for.
- Shorten the reading. Trace the change end to end first; the smallest diff in
  the wrong place is a second bug.

## Apply and check

Make one simplification at a time and re-run the affected tests after each. If a
"simpler" version is harder to read or review, revert it. For edits across many
files, script them instead of editing by hand.

Adapted from Addy Osmani's `code-simplification` and Lauren Tan's pstack
`principle-subtract-before-you-add` and `no-comments`, and the `ponytail` skill
(MIT; see UPSTREAM_LICENSE).
