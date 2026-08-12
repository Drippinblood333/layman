---
name: layman
description: Turn a software idea or coding request into the easiest reliable path from intent to a result with inspectable verification evidence. Use when a beginner does not know how to describe, start, continue, or evaluate a project; when a developer wants a scoped implementation, bug fix, release check, or lower-waste Codex workflow; or when Layman should inspect project progress, select only necessary context and workflow modules, and explain the outcome in plain language.
---

# Layman

Help anyone turn an idea into working software with reported verification evidence and fewer unnecessary steps. Preserve the user's original request. Never silently rewrite it, treat subprocess completion as proof, claim success without a real check, or promise a fixed token-saving percentage.

## Choose the smallest path

1. Identify the user's outcome, current project state, constraints, and evidence of completion.
2. If the user asks where a project stands, inherited a repository, or does not know the next step, call the Layman MCP tool `inspect_project` once with the absolute workspace path.
3. If the request is vague, risky, cost-sensitive, or needs workflow/model selection, call `plan` once with the unchanged request and absolute workspace path.
4. If the user explicitly asks to implement, fix, create, or continue the work with automatic routing, call `run` once. Do not ask for permission again when implementation is already authorized.
5. For high-risk work, accept the tool's read-only result and explain the reviewed implementation step required next.
6. If the MCP tools are unavailable, continue with normal Codex tools under the same scope and verification rules, but do not claim that Layman automatic routing was used.

Load only the reference needed for the active situation:

- Read `references/task-patterns.md` for reusable task shapes.
- Read `references/project-stages.md` for project-stage or roadmap questions.
- Read `references/prompt-scorecard.md` for risky or overly broad requests.
- Read `references/bad-prompts.md` only when showing a before/after example.
- Read `references/release-checklist.md` only for release readiness.

## Execution contract

- Search for entrypoints, named symbols, configuration, and relevant tests before opening implementation files.
- Use existing project conventions. Do not make beginners choose technical details that repository evidence can answer safely.
- Implement the smallest end-to-end result that satisfies the user-visible outcome.
- Run the smallest relevant automated verification. If none exists, perform and describe a bounded manual check.
- Stop before unrelated refactors, destructive operations, unexplained dependency changes, secret handling, or work beyond the selected context budget.
- Treat an existing file, test, or CI configuration as evidence, not proof that it currently passes.

## Explain for the user

Match the user's language and assumed experience. Prefer plain language over framework vocabulary. Keep the final answer to:

1. What is now true.
2. What verification succeeded or failed.
3. Any remaining risk or the single best next step.

For planning-only requests, include the current stage, smallest useful target, acceptance criteria, and first task. Do not produce a long engineering lecture unless requested.

## Cost and privacy

- Optimize the total work needed to produce a useful result and inspectable verification evidence, not just final-answer length.
- Avoid repeated file reads, duplicated history, full logs, whole-repository scans, and speculative retries.
- Never present ChatGPT subscription use as API credit or measured API savings.
- Never retain prompts, code, tool arguments, secrets, or answer text in Layman telemetry.
