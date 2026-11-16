---
name: handoff
description: Write a document a fresh session can continue from. Use this whenever the conversation is getting long, the user wants to continue later or in another session, or work is being passed to another agent.
---

# Handoff

Write a document a fresh agent can pick up without this conversation.

- The goal and the current state: what's done, what's in progress, what's next.
- Decisions made and why, and approaches tried that failed.
- Exact pointers: branch, commits, files, commands, issue and PR links. Reference
  specs, plans and issues by path or URL instead of copying them.
- Open questions and risks.
- Which skills the next agent should use.

If the user said what the next session is for, focus the document on that.
Redact secrets and personal data. Save it to the OS temp directory (`$TMPDIR`,
else `/tmp`), not the repository, and give the user the path.

Adapted from mattpocock/skills (skills/productivity/handoff) (MIT; see UPSTREAM_LICENSE).
