# Owner-approved local review trial — 2026-10-10

The owner explicitly approved the preceding proposal: at most eight new ChatGPT-subscription executions, synthetic tasks only, answers retained separately and locally for owner scoring. No upload of answers, paid API evaluation, tag or release is authorized.

This approval has its own cumulative reservation journal under ignored `build/private-plus-review-2026-10-10/`; the exhausted 12- and 36-execution journals remain unchanged. The existing exclusive writer, pre-execution fsynced reservations, first-failure stop and interrupted-reservation replay refusal apply. Failures consume budget; no automatic replacement experiment is authorized.

Four predeclared synthetic cases cover summary, rewriting, debugging and extraction, each with auto and always-deep arms. They are a small review-method trial, not an 18-case semantic acceptance, fresh public holdout, six-arm API comparison or invited-user acceptance. Execution order is fixed; alternated A/B presentation hides model labels but is not randomized or a robust latency comparison.

`scripts/private-plus-review.py` writes private answer artifacts and a local `REVIEW.md` through an explicit review sink. Answer text never enters the result JSONL or product telemetry on this path. The sink is absent by default and cannot be combined with the existing result-answer retention option. Private files remain ignored and must not be staged or uploaded.

Before launch: verify subscription login, preview exactly eight arms, and run the relevant offline budget/privacy tests. Score correctness, instruction following and clarity independently (0–2 each), recording factual errors; absent owner scores remain absent, not inferred or supplied by Codex.

Status: all eight executions completed, zero failures, zero incomplete usage and zero tool calls. All eight result keys match the eight persistent reservations; this approval is now 8/8 exhausted. Codex version: `0.162.0-alpha.2`; execution fingerprint: `535fa4704fd29ec5a98c071366dbb665322cf54cda23f3ccbdecb600a0ebe022`.

Eight separate local answer artifacts and the A/B review page exist under the ignored private directory; the result JSONL contains zero answer-text fields. Human scores remain absent. The full local suite passes 334 tests, configured lint, secret scanning and whitespace validation. Hosted verification of this review-sink change remains pending. No savings, human quality or release acceptance is claimed. This document contains no participant identities or raw answers.
