---
name: research
description: Look up how something is actually done, from primary sources, before deciding or building. Use this whenever a decision depends on a fact outside the repository (an API's behavior, a library's capabilities, a platform's limits, pricing, a version's changes), and before designing any new mechanism such as infrastructure, auth or tokens, an integration, scheduling, retries or caching, to find the standard approach and existing tools first. Use it even when you think you already know the answer, if being wrong would mean building the wrong thing.
---

# Research

Find out how the thing is really done before deciding, and keep the reading out of the main
conversation.

## Run it in the background

Start a subagent with a fresh context window and give it: the question, the decision it feeds,
what is already known or ruled out, and where to save the findings. Keep working while it reads.
For a quick fact (one doc page), just look it up yourself.

## What the researcher does

1. **Go to primary sources:** official docs, the source code, the spec, first-party APIs and
   changelogs. Follow every claim in a blog post or answer back to the source that owns it.
2. **For a new mechanism, find the standard way.** Look for the platform's native feature, the
   approach its docs recommend, and established open-source tools that already do it. Compare two
   or three options on fit, upkeep and risk. Name the one most people use for this exact problem.
3. **Check the facts that would change the decision:** limits, expiry, costs, versions,
   deprecations. Note the date and version each fact applies to.
4. **Write the findings** to one Markdown file: the question, the answer, the options compared and
   a recommendation, each claim with its source link. Save it where the repository keeps such
   notes; if there is no convention, use a scratch location and say where.

## Report back

Lead with the answer and the recommendation in two or three sentences, then the file path. Say
plainly what the sources didn't settle.

Adapted from Matt Pocock's `research` (MIT; see UPSTREAM_LICENSE).
