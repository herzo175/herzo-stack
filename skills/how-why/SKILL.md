---
name: how-why
description: "Explain how code works and why it was built that way, with file:line references and the commit and PR record. Use this whenever you're about to change unfamiliar code, the user asks how or why something works, or you need to decide where a change belongs."
---

# How and why

## How does it work

Explore the code and explain it so an engineer new to this area leaves with a
working model: the entry points, the main flow with `file:line` references, the
data it owns, and what calls it. For a big area, send a read-only subagent to
explore and present its explanation. State your interpretation if the question
is ambiguous; the user can redirect.

For "where should this live": name the module that owns the related state or
behavior, and the existing pattern the change should copy.

## Why is it this way

Answer from the record, not the code. Read the commits and PR discussions that
introduced the code and each later change (`git log -L`, `git log -S`,
`gh pr view`), plus linked issues or docs. Quote what the authors wrote, and mark
anything you infer as inference. If the record is thin, say so.

Adapted from cursor/plugins (pstack/skills/how, pstack/skills/why) (MIT; see UPSTREAM_LICENSE).
