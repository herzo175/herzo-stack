---
name: deslop
description: "Write plainly. Use this whenever you write or edit something people will read: a PR body, issue comment, commit message, doc, summary or report. It removes filler, AI vocabulary and inflated phrasing."
---

# Deslop

People act on what you write in PRs, comments and summaries. Say what happened
and what to do, plainly.

## Cut

- **Filler and hedging.** "It is important to note that", "in order to" (use
  "to"), "could potentially" (use "may"), generic closers ("this improves
  overall robustness").
- **AI vocabulary.** crucial, delve, enhance, leverage, robust, seamless,
  pivotal, showcase, underscore, comprehensive, utilize (use "use"), facilitate
  (use "help").
- **Inflated verbs.** "serves as", "stands as", "boasts": say "is" or "has".
- **Shapes.** "Not just X, but Y"; forced groups of three; em dashes; bold
  labels that restate the line ("**Performance:** Performance improved");
  decorative emoji; title-case headings.
- **Chat phrases.** "Great question", "I hope this helps", "Let me know if",
  "Found the smoking gun!".
- **Abstract nouns** where a concrete word exists: surface, substrate, vector,
  primitive, harness, paradigm, north star.

## Prefer

- The mechanism or the number over a feeling: "the collector streams each file to
  disk and holds one capture in memory", not "memory usage is now much better".
- Active voice with the actor named: "the loader rejects the row", not "the
  row is rejected".
- One idea per sentence, with articles and verbs. Spell out arrows and
  abbreviations.
- The same term for the same thing throughout.
- A sentence that could only appear in this project. If it could appear unchanged
  in any project's docs, cut it.

Adapted from Lauren Tan's pstack `unslop` (MIT; see UPSTREAM_LICENSE).
