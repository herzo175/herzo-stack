---
name: to-tickets
description: Split a plan, spec or conversation into end-to-end tickets with blockers, in the issue tracker. Use this whenever the user wants work broken into issues, assigned out, or tracked across sessions or people.
---

# To tickets

Turn work into tickets that each deliver something end to end.

1. Gather the plan, spec or conversation. If given an issue or file, read all of
   it, including comments.
2. Read the code it touches. Look for refactoring that would make the rest easy;
   that becomes the first ticket.
3. Draft vertical slices: each ticket cuts a narrow but complete path through
   every layer it needs (schema, logic, interface, tests), can be verified on its
   own, and fits in one fresh session. One mechanical change across the whole
   codebase (a rename) is the exception: keep it as one ticket.
4. Give each ticket its blockers: the tickets that must land first.
5. Show the breakdown as a numbered list (title, blocked by, what it delivers)
   and ask whether the size and blockers are right. Iterate until the user
   approves.
6. Publish in dependency order so blockers have real numbers to reference
   (`gh issue create`; use native sub-issues or "Blocked by #N" lines). Each
   ticket says what to build from the user's point of view, its blockers, and how
   to check it is done. Don't close or edit the parent issue.

Adapted from mattpocock/skills (skills/engineering/to-tickets, skills/engineering/to-spec) (MIT; see UPSTREAM_LICENSE).
