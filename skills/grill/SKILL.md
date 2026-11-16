---
name: grill
description: Reach a shared understanding of what to build before building it, through short rounds of questions with recommended answers. Use this whenever the user brings a new idea, feature, design or change that isn't fully specified, or says "grill me", before writing a plan or code. For efforts too big or foggy for one session, use plan in map mode.
---

# Grill

Reach a shared understanding of what to build before building it.

Map the decisions as a tree: each decision has the decisions that depend on it.
Work in rounds. The frontier is every decision whose prerequisites are already
settled. Ask the whole frontier in one round, numbered, each with your
recommended answer, worded so "yes" accepts it:

```
Q1. <title>: <one or two sentences, with the options if there are a few>
Recommended: <answer>, because <one-line reason it matters>
```

Keep each question that short. Long questions tire the user and hide why you're asking.

Facts are your job, not the user's. If a question needs a fact from the code,
docs or environment, look it up first (or send a subagent) instead of asking.

After each round, recompute the frontier and ask the next. Don't ask a question
whose answer depends on an unanswered one.

When the frontier is empty, write a short design sketch: the goal, the decisions
made, what is out of scope and the open risks. Wait for the user to confirm it
before acting. If the work is bigger than one session, suggest `plan` (map mode) or
`to-tickets` next.

Adapted from mattpocock/skills (skills/productivity/grilling) and obra/superpowers (skills/brainstorming) (MIT; see UPSTREAM_LICENSE).
