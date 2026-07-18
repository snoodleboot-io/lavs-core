---
name: claude-conventions-are-generated
description: .claude/conventions/ files are generated from .prompticorn config — edit the yaml, not the output
metadata:
  type: project
---

The `.claude/` tree (conventions, agents, workflows, subagents, skills) is **generated** by the prompticorn tool from `.prompticorn/.prompticorn.yaml`. Do NOT hand-edit files under `.claude/conventions/` — a regeneration overwrites them.

**Why:** This repo migrated from kilocode/promptosaurus → Claude Code. The generator emits the conventions; the yaml is the source of truth.

**How to apply:** To change conventions, edit the `project:` / `spec:` blocks in `.prompticorn/.prompticorn.yaml` and rerun the generator. If generated conventions show `_(not specified)_`, the corresponding yaml field is blank. Session files live in `.prompticorn/sessions/` (gitignored). Related: [[lavs-uses-duckdb-not-postgres]].
