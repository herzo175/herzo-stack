---
name: debugging
description: Find the cause of a bug with a reproducing loop before changing code. Use this whenever a test fails, a command or pipeline errors, output is wrong, something is flaky or slow, or a fix didn't work, even if the cause looks obvious. Don't patch symptoms, raise limits or add retries before running it.
---

# Debugging

Find the cause with a feedback loop, then fix it there. Reading code to build a
theory before you can reproduce the failure is the main way debugging goes wrong.

## 1. Build a loop that goes red

Get one command that reproduces the exact symptom, and run it. In rough order of
preference:

1. A failing test at the seam that reaches the bug.
2. A CLI or script run on a fixture input, diffed against known-good output.
3. A request (`curl`) against a running service.
4. A replay of a captured payload, log or event through the code path.
5. A small harness that calls the failing function with the real inputs.
6. For "sometimes wrong": loop the trigger many times until the failure rate is
   high enough to work with.
7. For "worked before": `git bisect run` with the loop as the check.

The loop is ready when it runs unattended, gives the same verdict each run, takes
seconds rather than minutes, and fails on this bug, not on something nearby. Redact
secrets from anything you show.

If you can't build a loop after trying, stop and say so: list what you tried and
what access or data would make it reproducible, instead of guessing at a fix.

## 2. Shrink it

Cut inputs, config and steps one at a time, re-running after each cut, until
every remaining part is needed for the failure.

## 3. Rank hypotheses

Write three to five causes, ranked, each with a prediction: "if X is the cause,
changing Y makes the failure go away". Discard any you can't state that way.

## 4. Test one at a time

Change one thing per probe. Prefer a debugger or REPL, then targeted logs at the
boundaries that separate hypotheses. Tag temporary logs with a unique prefix
(`[DEBUG-a4f2]`) so one grep removes them. For slowness, measure a baseline
first, then bisect; don't guess.

## 5. Fix at the cause

Fix the first place the system goes wrong, not where the symptom shows. Before
editing a function, find every caller (`grep -rn`): one fix in the shared
function beats a guard in the one caller the failure named, which leaves its
siblings broken. Don't
raise limits, add retries or catch-and-continue without a measurement that says
that is the cause. Turn the shrunk repro into a regression test where a real seam
exists (see the `tdd` skill); if no seam can reproduce it, say so in the PR.

## 6. Finish

- Re-run the original loop: it passes.
- The regression test passes, or its absence is explained.
- `grep` the debug prefix: no temporary logs remain.
- The commit or PR states which hypothesis was the cause.

Adapted from Matt Pocock's `diagnosing-bugs` and Lauren Tan's pstack
`principle-fix-root-causes`, and the `ponytail` skill (MIT; see UPSTREAM_LICENSE).
