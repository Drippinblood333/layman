---
name: layman-auto
description: Execute one coding task through the user's existing ChatGPT login with automatic workflow, model, reasoning, context, compaction, safety, and output controls. Use when a user asks Layman to implement, fix, create, or continue work with the easiest reliable automatic Codex route, especially when they do not know which model or development steps to choose.
---

# Layman Auto

Use the local `layman` MCP tool named `run` exactly once with the user's original task and the current workspace path. Optimize for a useful outcome with inspectable verification evidence, not the shortest isolated answer. A completed child process alone is not proof of correctness.

## Required behavior

1. Pass the original user task unchanged in `task`. Do not summarize, rewrite, duplicate, or place it in a shell command.
2. Pass the absolute current workspace path in `workspace`.
3. The tool verifies ChatGPT login, removes API billing environment variables, selects Luna/low, Terra/medium, or Sol/high, and starts an ephemeral Codex task.
4. Return the child task's outcome, reported verification evidence, remaining risk, and a short route summary. Do not repeat logs or full metadata, and do not strengthen a reported check into a guarantee.
5. If the tool reports a missing ChatGPT login, model unavailability, subscription limit, or timeout, report that exact category. Never retry through an API key.
6. High-risk tasks run read-only on the deep tier. Explain that a separate reviewed implementation task is required.

If the MCP tool is unavailable, run `layman codex-plus status` only to diagnose installation. Do not fall back to putting the task in a shell command or temporary file.
