---
name: layman-status
description: Explain how far a software project has progressed and the single best next step using bounded repository evidence. Use when a beginner asks what stage their project is in, whether it is finished or ready to release, what remains, how to start an inherited repository, or whether Codex actually completed the requested work.
---

# Layman Status

Call the Layman MCP tool `inspect_project` once with the absolute workspace path.

Explain the result in the user's language with four short parts:

1. Current evidence-based stage.
2. Evidence found, translated into plain language.
3. What the inspection cannot prove, especially whether tests, builds, installation, or deployment succeed.
4. The single best next task.

Do not read file contents merely to make the stage look more certain. Do not call a project release-ready from file presence alone. If the user asks for proof, use normal Codex tools to run the repository's actual verification commands and update the conclusion from those results.
