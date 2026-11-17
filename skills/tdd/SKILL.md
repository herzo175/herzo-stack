---
name: tdd
description: "Write a failing test before fixing a bug. Use this whenever you fix a bug that has a cheap local test path, or a regression test is asked for. If no practical test seam exists, use the closest executable regression check instead of building unrelated infrastructure."
---

# Test first for bug fixes

Make the broken behavior executable before changing production code: a focused
test that fails before the fix and passes after it.

1. State the intended behavior, the current behavior and the smallest
   reproduction.
2. Pick the narrowest check the repository already uses for that code path (unit,
   integration or regression test).
3. Write the smallest test that would have caught the bug. Assert what callers
   can observe, not implementation details.
4. Run it before fixing. It must fail for the intended reason; if it passes or
   fails for another reason, fix the test first.
5. Make the smallest production change that satisfies the intended behavior.
6. Re-run the test and the nearby tests.

Prefer no new test over a bad one: a test of mocks, of current implementation
strings, of timing or global state, or one that needs broad harness setup,
expensive infrastructure or unrelated fixture churn. Use the closest executable check instead (a script, a diff of
outputs) and say so.

Never change a test to match a wrong implementation or weaken an existing
assertion to make it pass. When you report, name the failing-before run and the
passing-after run.

Adapted from Lauren Tan's pstack `tdd` (MIT; see UPSTREAM_LICENSE).
