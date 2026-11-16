---
name: measure
description: "Check a number before reporting or acting on it. Use this whenever you're about to claim a speedup, memory or size figure, row count, cost, scale estimate or before/after comparison, even an informal one, so the claim survives a skeptical reviewer."
---

# Measure before you claim

A number you can't explain is a guess. Check it before it goes in a PR, a
report or a decision.

## Before you run

- Write the sentence you expect to ship ("peak memory 5.8 GiB → 1.2 GiB on the
  full import") and the result that would change your decision.
- Read the measurement script: what it times or counts, and what it skips.
- Check what else is running on the machine (`uptime`, core count) and note it.

## The questions

1. **Why not double?** Name what bounds the result: one core, memory, disk,
   network, the source's rate limit, a lock. Get it from a profile (`py-spy`,
   `top`, `/usr/bin/time -v`) in a run you don't report.
2. **Was it tuned?** Run both sides the way production runs: same data, flags,
   batch sizes, caches and versions. A side left on defaults compares settings,
   not code.
3. **Does it break a limit?** Check the arithmetic against bandwidth, cores and
   the share of time the changed piece took. A result past a physical limit
   measured a cache, a no-op or a bug.
4. **Did it error?** Count failures, retries and rejected rows, and check outputs
   are correct, not just present.
5. **Does it reproduce?** Run each side at least three times, alternating, and
   report the median and range. A gap smaller than the run-to-run spread is no
   difference.
6. **Does it matter?** Measure the end-to-end path at production size next to any
   micro result. A step that takes 10% of a run can make it at most about 11%
   faster.
7. **Did the work happen?** Confirm the rows were written, the bytes were read and
   lazy code (generators, unawaited calls) actually ran inside the timed region.

## Report

Lead with the verdict: better, worse, no measurable difference or inconclusive.
Give the number with its unit, run count, range and limiter. Call it
inconclusive when you can't name the limiter, a side ran untuned, or you
couldn't check questions 4 and 7. Keep the raw runs in an artifact or the PR.

Adapted from Lauren Tan's pstack `principle-explain-the-number` and
`benchmark-checklist` (MIT; see UPSTREAM_LICENSE).
