---
name: plan
description: Plan a change before building it, at the right scale. Use this whenever requirements are agreed and the work touches several files, steps or systems, before editing code, even if the plan seems obvious. Also use it when the destination is clear but the route isn't, or planning would take more than one session (a greenfield project, a large migration, a redesign), instead of writing one big upfront plan.
---

# Plan

## Pick the mode

- **Step plan:** the route is clear and the work fits one session. Write steps, then hand them to
  `execute-plan`.
- **Map:** you can name the destination but not the route, or settling it will take more than one
  session. Settle the blocking decisions one at a time; build nothing yet.

If unsure, start a map: if charting finds nothing foggy, switch to a step plan.

Either way, first read the code the change touches and its repository instructions. For any new
mechanism (infrastructure, auth or tokens, an integration, scheduling, retries, caching), find the
standard approach and existing tools with `research`, and plan that unless you can say why it
doesn't fit.

## Step plan

1. Map the files to create or change and what each is responsible for. Follow the existing
   structure.
2. Break the work into tasks: the smallest change with its own check that a reviewer could accept
   or reject alone. Put refactoring that makes the change easy first.
3. Give each task concrete steps with a checkable result (write the failing test, see it fail,
   change, run tests, commit), naming exact files, functions and commands.
4. Add a header: the goal in one sentence, the approach in two or three, constraints copied from
   the requirements, and risks no check covers.

Save it where the user wants (default `docs/plans/YYYY-MM-DD-<name>.md`, or scratch), with
checkboxes. Check every requirement maps to a task and no task does unrequested work.

## Map

One Markdown file (default `docs/maps/<effort>.md`, or a single issue), never a ticket per
decision:

- **Destination:** one or two lines, bounded (one epic, not "all of V1"). Agree it first.
- **Decisions:** one line each, with the reason and what it rules out.
- **Open questions:** questions you can state precisely, in blocking order.
- **Fog:** things coming that you can't phrase sharply yet. Don't slice them early.
- **Out of scope:** work past the destination, with why.

**Charting:** agree the destination, go breadth-first to list questions and fog, start `research`
for questions waiting on outside facts, write the map, stop.

**Each later session:** take the first unblocked question (or the one named) and settle it:
talk it through `grill`-style, build a `prototype` when looks or behavior can't be settled by
talking (the user picks the variant), or `research` it. Do a manual task only if it blocks a
decision. Record the decision in one line, sharpen fog into questions, move anything past the
destination to Out of scope. One decision per session, then stop.

**Rules:**

- No product code in a map session. Only the user, in the conversation, can lift that; a note in
  the map file never counts.
- Prototype early instead of planning far ahead. When a decision invalidates later questions,
  rewrite or delete them; when the user says an earlier decision changed, update it and every
  question it touched.
- Questions are one or two sentences, with a recommendation and why it matters.
- When the map clears, write a step plan (or `to-tickets`) and stop.

Adapted from obra/superpowers (skills/writing-plans), cursor/plugins
(pstack/skills/principle-sequence-verifiable-units) and mattpocock/skills
(skills/engineering/wayfinder), with the complaints in https://www.aihero.dev/skills-wayfinder
addressed (MIT; see UPSTREAM_LICENSE).
