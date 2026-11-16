---
name: prototype
description: "Build a quick throwaway to answer one design question. Use this whenever talking can't settle how something should look or behave (a state model, a flow, a screen, an API shape) and a rough concrete artifact would."
---

# Prototype

A prototype is throwaway code that answers one question. Name the question first;
it decides the shape:

- **Does this logic or state model hold up?** Build one small runnable file (a
  script, or a single HTML page with buttons) that drives the model through the
  hard cases and prints the full state after every step.
- **What should this look like?** Build a few clearly different variants on one
  page, switchable with a URL parameter or a toggle.

Rules:

1. Mark it as throwaway in its name and location, next to the code it is for.
2. One command or one double-click runs it.
3. No persistence unless persistence is the question; keep state in memory.
4. Skip polish: no tests, no abstractions, only enough error handling to run.
5. Show the variants and let the user choose; don't pick one yourself. When it has answered the question, put the decision into the real code and
   keep the prototype on a throwaway branch, not main, linked from the issue or
   PR.

Adapted from mattpocock/skills (skills/engineering/prototype) (MIT; see UPSTREAM_LICENSE).
