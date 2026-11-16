---
name: blast-radius
description: "Find what a change could break beyond its diff, and prove the facts its safety rests on. Use this before merging or shipping anything you don't fully trust: shared code, data formats, migrations, config, concurrency or auth, or whenever the user asks what could break."
---

# Blast radius

Find what a change could break elsewhere, and prove the facts its safety rests
on. Listing callers is the easy part; the job is the breakage grep won't show:
shared state, ordering, config, serialized formats, caches, other services and
data already written.

## How sure are you

For each fact the change's safety depends on, get it as far down this list as is
cheap, and say where you stopped:

1. Someone said so. Worth nothing on its own.
2. You pointed at the `file:line` or the library's source.
3. You walked the failure case step by step and showed it can't happen.
4. You ran it: a small script or test that calls the real code and fails loudly
   if the fact is wrong.
5. You reproduced it in the running system.

Step 4 is usually one small script that imports what the app ships and calls
the function you're worried about.

## Report

The facts the change depends on, how far each got, what you ran and its output,
and anything that could break that you couldn't rule out.

Adapted from cursor/plugins (pstack/skills/blast-radius) (MIT; see UPSTREAM_LICENSE).
