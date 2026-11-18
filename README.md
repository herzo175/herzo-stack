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
| `simplify-diff` | Clean up your own diff without changing behavior. | Addy Osmani, pstack and ponytail |
| `deslop` | Write plainly. | Lauren Tan's pstack `unslop` |
| `correct` | Make a repeated mistake impossible instead of adding another rule. | Lauren Tan's pstack `correct` |
| `grill` | Reach a shared understanding of what to build before building it, through short rounds of questions with recommended answers. | mattpocock/skills (skills/productivity/grilling) and obra/superpowers (skills/brainstorming) |
| `plan` | Plan a change before building it, at the right scale: a step plan, or a decision map for foggy multi-session efforts. | obra/superpowers (skills/writing-plans), pstack and mattpocock/skills (wayfinder) |
| `execute-plan` | Carry out a written plan task by task, checking each step and recording decisions. | obra/superpowers (skills/executing-plans, skills/subagent-driven-development) and cursor/plugins (pstack/skills/principle-sequence-verifiable-units) |
| `to-tickets` | Split a plan, spec or conversation into end-to-end tickets with blockers, in the issue tracker. | mattpocock/skills (skills/engineering/to-tickets, skills/engineering/to-spec) |
| `how-why` | Explain how code works and why it was built that way, with file:line references and the commit and PR record. | cursor/plugins (pstack/skills/how, pstack/skills/why) |
| `blast-radius` | Find what a change could break beyond its diff, and prove the facts its safety rests on. | cursor/plugins (pstack/skills/blast-radius) |
| `second-opinion` | Get a fresh-context reviewer to try to break a decision, change or claim before it stands. | cursor/plugins (pstack/skills/interrogate) and addyosmani/agent-skills (skills/doubt-driven-development) |
| `handoff` | Write a document a fresh session can continue from. | mattpocock/skills (skills/productivity/handoff) |
| `prototype` | Build a quick throwaway to answer one design question. | mattpocock/skills (skills/engineering/prototype) |

## Install

Pick one route per agent. Installing the same skills twice (say, as a Claude Code plugin and
through `npx skills`) gives the agent duplicate entries.

### Claude Code

```text
/plugin install herzo-stack --marketplace herzo175/herzo-stack
```

Or from a shell:

```bash
claude plugin marketplace add herzo175/herzo-stack
claude plugin install herzo-stack@herzo-stack
```

Update with `claude plugin marketplace update herzo-stack` and then
`claude plugin update herzo-stack@herzo-stack`.

### Codex

```bash
codex plugin marketplace add herzo175/herzo-stack
codex plugin add herzo-stack@herzo-stack
```

Update with `codex plugin marketplace upgrade`.

### Capy cloud

In Settings → MCP & plugins, choose **From GitHub repository** and enter
`https://github.com/herzo175/herzo-stack`. Choose **Organization** and **All projects**
to share the skills with the team. The root `plugin.json` and `mcp.json` package the
same `skills/` tree using the Agent Plugins format; no MCP servers or keys are needed.

New cloud threads discover the installed skills. Click **Sync** on the plugin page
to pull GitHub updates. Remove earlier Drive copies of these skills after verifying
the plugin, since Drive skills take precedence over plugin skills.

### Any agent, with `npx skills`

[skills.sh](https://skills.sh) installs into `~/.agents/skills` (read by Codex and others) and
links each skill into the agents you name, such as Claude Code:

```bash
npx skills add herzo175/herzo-stack -g -s '*' -a claude-code -a codex
```

Update with `npx skills update -g -y`; re-run `add` to pick up skills added later. This is the
route the author uses, so one install covers both Claude Code and Codex.

### From a clone, while editing

```bash
git clone https://github.com/herzo175/herzo-stack ~/Documents/projects/herzo-stack
cd ~/Documents/projects/herzo-stack
for skill in skills/*/; do
  name=$(basename "$skill")
  ln -sfn "$PWD/$skill" ~/.agents/skills/"$name"
  ln -sfn ../../.agents/skills/"$name" ~/.claude/skills/"$name"
done
```

Edits are live immediately. Remove these links before switching to another route.

### Global instructions (optional)

To tell agents these skills exist and to suggest improvements to them, put a short
`~/.agents/AGENTS.md` that lists the skills and link it as `~/.claude/CLAUDE.md` and
`~/.codex/AGENTS.md`.

## Writing a skill here

- The description says what the skill does and lists the concrete situations that should trigger
  it, ending with "even if…" where models tend to skip it. No "MUST" or "ANY", and no
  session-start bootstrap.
- Before building a new mechanism, the skill should point at `research` to find the standard
  approach first.
- Quote the description in double quotes: an unquoted `: ` inside it breaks YAML for some
  installers (the `skills` CLI skips the skill).
- Keep the body under about 800 tokens; put long references in a separate file the body links to.
- Keep upstream licenses in `UPSTREAM_LICENSE` when adapting someone else's skill.
- When you add or remove a skill, update `.claude-plugin/plugin.json` (`skills`) and the table
  above, and bump `version` so plugin installs pick it up.

## Evaluate changes

The [behavioral eval suite](evals/README.md) runs conversation-derived tasks through isolated
Pi or OpenCode sessions, compares pinned skill versions, and grades actual outcomes with
Pydantic Evals and OpenRouter. Raw conversation histories stay local. Model-funded runs are
explicit or opt-in; behavioral verdicts initially inform review rather than block merges.
