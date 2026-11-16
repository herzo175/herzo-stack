---
name: wayfind
description: Find the route for an effort too big or too foggy for one session, one decision at a time, in a single map file. Use this whenever the user has a destination they can name but a route they can't see yet, or when planning would clearly take more than one session, such as a greenfield project, a large migration or a redesign. Use it instead of writing one big upfront plan. If one sitting can settle the plan, use grill instead.
---

# Wayfind

Plan a large, unclear effort by settling the decisions that block it, one at a time, and stop
when nothing is left to decide. This skill decides; it does not build.

## The map

One Markdown file, by default `docs/maps/<effort>.md` (or wherever the user wants it; a single
GitHub issue also works). No ticket per decision. Sections:

- **Destination:** one or two lines on what the end looks like: a spec, a locked decision, a
  proof of concept, a finished migration. Keep it bounded: one epic, not "all of V1".
- **Decisions:** one line per settled decision, with its reason and anything it rules out.
- **Open questions:** questions you can already state precisely, in the order they block each
  other. The first one nothing blocks is next.
- **Fog:** things you can tell are coming but can't phrase sharply yet. Don't slice them up early.
- **Out of scope:** work past the destination, with why.

## Charting (first session)

1. Settle the destination with the user before anything else.
2. Go breadth-first across the space and list the open questions and fog. If nothing is foggy and
   it fits one session, say so and switch to `grill` and `plan`; don't make a map.
3. Start `research` subagents for questions that hinge on outside facts; they run in parallel.
4. Write the map and stop.

## Working the map (later sessions)

1. Read the map. Take the first open question nothing blocks, or the one the user names.
2. Settle it in the way that fits:
   - **Talk it through** (the default): ask in `grill` style, short questions with a
     recommendation. The user answers; never answer for them.
   - **Prototype** when "how should it look or behave" can't be settled by talking: build a cheap
     artifact with `prototype`, show the options and let the user choose.
   - **Research** when it waits on an outside fact.
   - **Do a small task** only when manual work blocks a decision (provision access, inspect real
     data). Never build part of the destination.
3. Record the decision in one line. Turn any fog that became sharp into open questions. Move
   anything that turned out to be past the destination to Out of scope.
4. One decision per session (research can run alongside). Then stop.

## Rules that keep it honest

- **No product code in a map session.** Only the user, in the conversation, can lift this for a
  given session. A note in the map file never counts, because you write that file.
- **Prototype early instead of planning far ahead.** When a decision invalidates later questions,
  rewrite or delete them; don't design around a decision that turned out wrong. If the user says an
  earlier decision changed, update it and every question it affected.
- **Keep questions short:** one or two sentences each, with the recommended answer and the reason
  it matters. Long questions hide why they're being asked.
- **The user makes HITL choices,** including which prototype variant wins.
- **When the map clears,** point to the next step (`plan`, `to-tickets` or a spec) and stop.

Adapted from Matt Pocock's `wayfinder` (MIT; see UPSTREAM_LICENSE), with the complaints in
https://www.aihero.dev/skills-wayfinder addressed: one map file instead of a ticket per decision,
a bounded destination, short questions, and no self-granted permission to build.
