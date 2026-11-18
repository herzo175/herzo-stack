# Audited evaluation corpus

The cases come from a contextual audit of local Codex and Claude conversations and actual
Factory worker/reviewer histories. They are **sanitized reconstructions**, not copies of raw
transcripts or exact historical workspace replays.

The audit covered:

- Thirteen main Codex sessions across multiple project areas, with user-event filtering and
  surrounding assistant/tool context. The largest session was sampled at its beginning and
  end; its middle was not exhaustively reviewed.
- Fourteen top-level Claude sessions indexed, with six sessions contextually reviewed across
  five project areas. Automated monitor prompts, stop hooks, and subagent messages that look
  like user messages were excluded.
- Two hundred recent Factory runs, twenty-nine initial worker streams, and five targeted
  reviewer histories. The audit compared review findings with collected native tool output
  where available; some incidents remain supported only by the review observation. A successful
  reviewer run does not mean its PR was accepted.

The private audit identified twenty-five Codex, twenty-three Claude, and eighteen Factory
candidate families before overlap and coverage selection. Those candidate counts are not
independent verified historical bugs. Exact pre-error workspaces were not recovered. The
published fixtures reproduce the relevant expectation or failure mechanism in a small local
application, and their reference implementations establish solvability.

Public catalogues under `corpus/` label each case's family, source aliases, origin, scope,
skills and held-out status. `incident_reconstruction` means its expectation is supported by
reviewed source context; `designed_extension` adds follow-up work or a controlled compaction
boundary; `designed_control` tests a counterexample or skill contract without claiming a
recovered incident. Private pointers, offsets, timestamps, hashes and contextual audit notes
remain in the ignored local `.secrets/eval-provenance/` directory. Raw histories and credentials
are not committed or sent to the Actions evidence artifacts.

## Coverage

There are 53 cases: 41 incident reconstructions, six designed extensions, and six controls.
Fourteen are held out. The suite includes thirty-eight checkpoints, twelve multi-turn episodes,
and three forced-compaction episodes, with explicit coverage for every skill in the pack.

The source-derived cases include:

- Unsupported compatibility versus actual client contracts; one-time migrations versus
  permanent scaffolding; native SDK/CLI contracts versus custom protocols.
- Authoritative source links, published availability, version-specific options, retrieval
  versus citations, observed job state and unsupported estimates.
- Current instructions versus historical lessons, shared versus project guidance, read-only
  diagnosis, targeted checks and preserving intentional product behavior.
- Factory findings about listing counts, additive schema fields, NaN-aware parity, binary
  geometry variants, invalid-input contracts, error attribution, derived JSON rule paths,
  actual framework/executor entry points, completeness witnesses, evidence hashes and failing
  check exit codes.
- Multi-turn scope and tool-preference retention, with a small set of **actual forced native
  compactions**. These are accelerated stress tests, not evidence of hours-long reliability or
  natural context exhaustion. Durable project files remain available; unaided recall is not
  the goal.

Each case has independently run outcome checks and a known-good reference. Relevant broken
outcomes are tested too. Additional adversarial grading tests protect against plausible partial
fixes and valid alternative solutions. Process and prose criteria use ordered tool evidence and
an LLM rubric; the narrow outcome checks do not establish those criteria alone.

## Running and interpreting

Use `herzo-evals --list --include-held-out` to inspect the current case IDs. Run a single case
first. Actions partitions larger selections into disjoint groups sized for the trial timeout,
judge deadline, number of arms and repetitions, with at most two groups running concurrently.
A current-pack characterization needs only the candidate arm; a skill-change comparison uses
both released and proposed versions with the runtime/model held fixed.

The held-out set is for release checks, not routine prompt tuning. Behavioral results remain
report-only. Review verdicts and traces before interpreting aggregate numbers, and calibrate
judges against human labels before using them to block merges. Reference tests passing means
the graders accept a known solution; it does not mean an agent solved the corpus. Native CLI
integration pilots likewise do not establish that a new skill version improves quality.
