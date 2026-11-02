---
disable-model-invocation: true
name: research
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
---

Spin up a **background agent** to do the research, so you keep working while it reads. Start it with a fresh context window.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source.
3. Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.

## Dentix adaptation

Use this skill only when explicitly requested by the owner, selected by an AGENTS.md routing rule, or required as a documented dependency of an explicitly authorized skill. This skill never overrides AGENTS.md, PROJECT_STANDARDS.md or DEVELOPMENT_WORKFLOW.md. Stay within the authorized task scope.

Save findings under docs/reports/ only after the owner approves the file name.
