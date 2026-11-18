# Skill evaluations

This suite measures whether herzo-stack changes improve real coding-agent behavior. It is
separate from Factory's tests for packaging and delivering skills.

Pydantic Evals runs the experiments and graders. The coding agent remains the real Pi or
OpenCode CLI, running inside a fresh Docker container for each conversation episode. OpenRouter
provides the agent and judge models. There is no fallback to an unrestricted local agent.

## Setup

Use Python 3.11+, [uv](https://docs.astral.sh/uv/), and Docker with a running daemon:

```bash
uv sync --project evals --frozen
docker build -t herzo-evals:local evals/container
uv run --project evals herzo-evals --list --include-held-out
```

Set `OPENROUTER_API_KEY` in your environment. Keep it out of prompts, command arguments, Git,
and transcripts. A local ignored `.secrets/openrouter.env` can hold `OPENROUTER_API_KEY=…`;
load only that value using your secret manager or environment loader. Use `uv run --env-file .secrets/openrouter.env --project evals …` to load it without
executing shell code. The runner does not execute or shell-source dotenv files. GitHub uses the Actions secret of the same name.

Choose explicit OpenRouter model IDs for both roles. The judge can be different from the agent;
both use OpenRouter. Use the same agent model when comparing skill versions. The suite does
not silently fall back to another model on an error.

```bash
uv run --project evals herzo-evals \
  --runtime pi --kind checkpoint \
  --model '<provider/agent-model>' --judge-model '<provider/judge-model>' \
  --baseline-ref e45aa78eaec30be8c291989a766ba9153f0e7626 \
  --repeat 2 --concurrency 1 --output evals/results/first-comparison
```

To establish the current pack's baseline without paying for two identical skill trees, replace
`--baseline-ref …` with `--candidate-only`. This is characterization, not evidence of a skill
improvement. `--shard INDEX/TOTAL` selects a deterministic disjoint partition; `--matrix` prints
the matching bounded CI matrix without Docker, model calls, or credentials.

Each arm gets the same scenarios, runtime, model, and limits. The baseline's skill tree is
restored from the exact Git commit; the candidate uses `skills/` from this checkout. Manifests
record content hashes, the model IDs, limits, and Docker image ID. `--no-skill-baseline` measures
whether the guidance helps at all. Select it instead of `--baseline-ref`.

Use `--runtime opencode --kind checkpoint` for a separate runtime experiment. Do not attribute
a result to skills if the runtime, model, or configuration also changed. The adapter boundary
can be extended to Codex or Claude Code; those adapters are not implemented in this first
version. Native saved sessions are not portable between runtimes.

## Multi-turn and compaction

One trial is a whole episode. Follow-up prompts go to the same session, using actual generated
code and tool results. They are not a pasted historical transcript.

```bash
uv run --project evals herzo-evals \
  --runtime pi --kind compaction --include-held-out \
  --model '<provider/agent-model>' --judge-model '<provider/judge-model>' \
  --baseline-ref e45aa78eaec30be8c291989a766ba9153f0e7626 \
  --repeat 1 --output evals/results/compaction-pilot
```

Compaction cases require a successful native Pi compaction action followed by more work, with
observed compaction evidence. The forced case records a 1,024-token recent-history policy and
requires that the original instruction is removed from the active context and replaced by a
summary. This is an accelerated stress case, not the runtime's default retention policy. It does
not establish reliability across hours of work or natural
context exhaustion. OpenCode compaction is currently unsupported and rejected explicitly.
See [the audited corpus](CORPUS.md) and [initial case limitations](CASES.md). The held-out flag separates development cases
from a release check set; once you tune against a case, treat it as development data and add
new held-out cases. It is a workflow convention, not access control.

## Grading and results

Each trial saves normalized chronological events, the final code diff, independent checks,
termination status, observed usage, and elapsed duration. Binary outputs are represented by
byte counts and SHA-256 hashes rather than undecodable text; code diffs and independent data
checks remain available. Each completed case also saves its
verdict immediately using Pydantic's lifecycle hook, so interrupting a later case does not erase
already graded results. Private raw conversation archives are
never uploaded. Fixture prompts and source are visible to the coding agent; rubric and grader
commands stay outside its session. Independent checks run after the agent has stopped.

Deterministic checks establish observable behavior. A separate LLM judge receives explicit
user turns, tool events, diff, and actual check results. It has no access to the agent's process
or files and cannot infer success from a claimed completion. Pi's cumulative UI snapshots are normalized before the capture budget is applied. Artifacts
retain linear streaming deltas, finalized visible messages, ordered tool arguments/results and
compaction summaries/validation, without repeated aggregate copies. The judge omits streaming
deltas and internal reasoning text. Full native context is used internally to validate compaction;
its duplicate snapshots are not persisted. The judge input is capped at 200,000 characters, calibrated against a completed six-turn
compaction episode (137,020 characters after removing repeated snapshots). The manifest records
this cap. Oversized evidence, judge errors and execution
failures are reported explicitly rather than treated as favorable truncation or behavior scores.

The CLI exits unsuccessfully for execution/judge failures. A completed trial with failing
behavior or correctness checks remains **report-only**: inspect the per-case assertions in
`comparison.json` and the evidence under each arm. Do not treat the workflow's green status as
proof of skill quality. No quality improvement is claimed until trials have run and their
judges have been reviewed.

Before enabling a behavioral merge gate, label representative good/bad outputs yourself,
compare the judge's verdicts with those labels, and revise ambiguous rubrics. Preserve those
labels and rerun calibration when changing the judge or rubric. Do not retry a failing behavior
until it passes; retain every attempt. Provider outages and missing evidence are distinct from
an agent choosing the wrong implementation.

## GitHub Actions

`.github/workflows/evals.yml` runs offline checks for relevant PRs and main changes. Use
**Actions → Skill evals → Run workflow** for paired or characterization trials: choose a runtime, episode
type, explicit agent/judge model IDs, baseline commit, and repetitions. Select a single case ID for a small pilot. Enable the held-out checkbox for release checks, including
the compaction suite; ordinary PR runs exclude those cases. Full evidence is kept
as separate shard artifacts for seven days; the job summary shows per-case results.

A full Pi selection uses the `all` suite. OpenCode supports the checkpoint and episode suites;
manual compaction still requires Pi. Shards account for repetitions and both arms, reserve
setup/cleanup time, and run at most two jobs concurrently. In characterization mode, each case
runs once per requested repetition, with no duplicate baseline arm.

Recurring paid runs are opt-in after measuring a pilot:

- `EVAL_PR_RUNS_ENABLED=true` enables checkpoint comparisons for same-repository skill PRs.
- `EVAL_SCHEDULE_ENABLED=true` enables the weekly Pi compaction suite.
- Both require repository variables `EVAL_MODEL`, `EVAL_JUDGE_MODEL`, and optionally
  `EVAL_BASELINE` (default: the released commit above), plus `OPENROUTER_API_KEY` as a secret.

Fork PRs get offline checks only. Model-funded runs use trusted refs and a read-only GitHub
token; the agent container receives no repository write token or production cloud credentials.
Limits include concurrency, episode timeout, bounded output, and a separate judge deadline.
Reported usage is the runtime's observed agent usage; it excludes judge calls and may omit
compaction usage. These bounds do not enforce a precise dollar spend: check OpenRouter billing
after the pilot and configure a spending limit on the key. Docker cleanup runs on success, failure, and cancellation.

## Develop

```bash
uv run --project evals --frozen pytest evals/tests -q
uv run --project evals --frozen ruff check evals
uv run --project evals --frozen ruff format --check evals
```

Add general cases here; keep Factory-specific integration checks in Factory. A case should
include a solvable fixture, realistic user prompt, clear criterion, independent check, and honest
provenance. Test checks against a known-good reference implementation and a bad starting state.
Avoid grading one exact implementation when multiple solutions satisfy the request.
