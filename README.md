# herzo-stack

Personal agent skills for Claude Code, Codex and other harnesses that read `SKILL.md`
directories. Each skill is short (a few hundred tokens), has a concrete trigger in its
description, and assumes an agent working with a person, not alone.

They're adapted from [obra/superpowers](https://github.com/obra/superpowers),
[mattpocock/skills](https://github.com/mattpocock/skills), Lauren Tan's
[pstack](https://github.com/cursor/plugins/tree/main/pstack),
[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) and ponytail, keeping
what helped and cutting always-on bootstraps, "MUST" triggers and ticket sprawl.

| Skill | What it does | Adapted from |
| --- | --- | --- |
| `research` | Look up how something is actually done, from primary sources, before deciding or building. | Matt Pocock's `research` |
| `debugging` | Find the cause of a bug with a reproducing loop before changing code. | Matt Pocock's `diagnosing-bugs` and Lauren Tan's pstack `principle-fix-root-causes`, and the `ponytail` skill |
| `tdd` | Write a failing test before fixing a bug. | Lauren Tan's pstack `tdd` |
| `measure` | Check a number before reporting or acting on it. | Lauren Tan's pstack `principle-explain-the-number` and `benchmark-checklist` |
| `simplify-diff` | Clean up your own diff without changing behavior. | original |
| `deslop` | Write plainly. | Lauren Tan's pstack `unslop` |
| `correct` | Make a repeated mistake impossible instead of adding another rule. | Lauren Tan's pstack `correct` |
| `grill` | Reach a shared understanding of what to build before building it, through short rounds of questions with recommended answers. | mattpocock/skills (skills/productivity/grilling) and obra/superpowers (skills/brainstorming) |
| `wayfind` | Find the route for an effort too big or too foggy for one session, one decision at a time, in a single map file. | Matt Pocock's `wayfinder` |
| `plan` | Write a step-by-step plan with a check for every step. | obra/superpowers (skills/writing-plans) and cursor/plugins (pstack/skills/principle-sequence-verifiable-units) |
| `execute-plan` | Carry out a written plan task by task, checking each step and recording decisions. | obra/superpowers (skills/executing-plans, skills/subagent-driven-development) and cursor/plugins (pstack/skills/principle-sequence-verifiable-units) |
| `to-tickets` | Split a plan, spec or conversation into end-to-end tickets with blockers, in the issue tracker. | mattpocock/skills (skills/engineering/to-tickets, skills/engineering/to-spec) |
| `how-why` | Explain how code works and why it was built that way, with file:line references and the commit and PR record. | cursor/plugins (pstack/skills/how, pstack/skills/why) |
| `blast-radius` | Find what a change could break beyond its diff, and prove the facts its safety rests on. | cursor/plugins (pstack/skills/blast-radius) |
| `second-opinion` | Get a fresh-context reviewer to try to break a decision, change or claim before it stands. | cursor/plugins (pstack/skills/interrogate) and addyosmani/agent-skills (skills/doubt-driven-development) |
| `handoff` | Write a document a fresh session can continue from. | mattpocock/skills (skills/productivity/handoff) |
| `prototype` | Build a quick throwaway to answer one design question. | mattpocock/skills (skills/engineering/prototype) |

## Install

Link the skills into the directories your harnesses read, so edits here are live:

```sh
for skill in skills/*/; do
  name=$(basename "$skill")
  ln -sfn "$PWD/$skill" ~/.agents/skills/"$name"        # Codex and others
  ln -sfn ../../.agents/skills/"$name" ~/.claude/skills/"$name"  # Claude Code
done
```

## Writing a skill here

- The description says what the skill does and lists the concrete situations that should trigger
  it, ending with "even if…" where models tend to skip it. No "MUST" or "ANY", and no
  session-start bootstrap.
- Before building a new mechanism, the skill should point at `research` to find the standard
  approach first.
- Keep the body under about 800 tokens; put long references in a separate file the body links to.
- Keep upstream licenses in `UPSTREAM_LICENSE` when adapting someone else's skill.
