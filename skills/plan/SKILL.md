---
name: plan
description: Write a step-by-step plan with a check for every step. Use this whenever requirements are agreed and the change touches several files, steps or systems, before editing code, even if the plan seems obvious. Hand the result to execute-plan.
---

# Plan

Write a plan someone who hasn't seen the codebase could execute.

1. Read the code the change touches and its repository instructions first. For any
   new mechanism (infrastructure, auth or tokens, an integration, scheduling,
   retries, caching), look up how the platform or ecosystem recommends doing it:
   official docs and established tools (use the `research` skill). Compare two or
   three options, including a native feature and an existing tool, and plan the
   standard one unless you can say why it doesn't fit.
2. Map the files to create or change and what each one is responsible for.
   Follow the existing structure; split a file only when you are already
   changing it and it has grown unwieldy.
3. Break the work into tasks. A task is the smallest change that has its own
   check and that a reviewer could accept or reject on its own. Fold setup and
   docs into the task that needs them. Put any refactoring that makes the change
   easy first.
4. Give each task concrete steps, each with a result you can check: write the
   failing test, run it and see it fail, make the change, run the tests, commit.
   Name exact files, functions and commands.
5. Add a short header: the goal in one sentence, the approach in two or three,
   constraints copied exactly from the requirements, and the risks no task's
   checks cover.

Save the plan where the user wants it (default: `docs/plans/YYYY-MM-DD-<name>.md`,
or a scratch file if the repo shouldn't hold it). Use checkboxes for steps.
Review it once against the requirements: every requirement maps to a task, and
no task does work nobody asked for. Then hand it to `execute-plan`.

Adapted from obra/superpowers (skills/writing-plans) and cursor/plugins (pstack/skills/principle-sequence-verifiable-units) (MIT; see UPSTREAM_LICENSE).
