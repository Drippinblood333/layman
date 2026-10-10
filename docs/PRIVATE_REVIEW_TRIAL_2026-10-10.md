# Owner-approved local review trial — 2026-10-10

## User-confirmed assistant review (not independent blind scoring)

On 2026-10-10 the assistant reviewed all eight answers and proposed 2/2 for
correctness, instruction following and clarity for each. The owner explicitly
accepted that recommendation. The local review page records those scores and
their provenance: **assistant-assisted, user-confirmed scoring**, not independent
human reviews. Code snippets were not executed in this content review. Original
result JSONL records, including null `human_score` fields, remain unchanged;
the eight local answer hashes match them. Raw answers remain private.

Offline aggregation of the existing four pairs:

| Metric | Auto | Always-deep |
| --- | ---: | ---: |
| Input tokens (including cached input) | 63,448 | 66,765 |
| Cached input tokens | 58,240 | 66,048 |
| Uncached input tokens | 5,208 | 717 |
| Output tokens | 360 | 352 |
| Total input + output tokens | 63,808 | 67,117 |

Auto total tokens are 4.93% lower in this specific sample, while output tokens
are higher and uncached input differs substantially. Per-pair total changes
(auto relative to deep) are summary +9.55%, rewrite -11.60%, debugging -11.75%
and extraction -4.01%. This is not an API cost measurement, a representative
development-task benchmark or a causal estimate of prompt-compression savings.
Fixed execution order, tiny sample, differing models/cache behavior and
assistant-assisted scoring prevent a general quality-equivalent savings claim.
The newer lean execution contract has a different fingerprint and cannot
inherit this result. Approval stays exhausted at 8/8; no execution was launched.
Broader claims require separately approved, predeclared evaluation and
independent quality evidence.

## Original execution record (historical)

The owner explicitly approved the preceding proposal: at most eight new ChatGPT-subscription executions, synthetic tasks only, answers retained separately and locally for owner scoring. No upload of answers, paid API evaluation, tag or release is authorized.

This approval has its own cumulative reservation journal under ignored `build/private-plus-review-2026-10-10/`; the exhausted 12- and 36-execution journals remain unchanged. The existing exclusive writer, pre-execution fsynced reservations, first-failure stop and interrupted-reservation replay refusal apply. Failures consume budget; no automatic replacement experiment is authorized.

Four predeclared synthetic cases cover summary, rewriting, debugging and extraction, each with auto and always-deep arms. They are a small review-method trial, not an 18-case semantic acceptance, fresh public holdout, six-arm API comparison or invited-user acceptance. Execution order is fixed; alternated A/B presentation hides model labels but is not randomized or a robust latency comparison.

`scripts/private-plus-review.py` writes private answer artifacts and a local `REVIEW.md` through an explicit review sink. Answer text never enters the result JSONL or product telemetry on this path. The sink is absent by default and cannot be combined with the existing result-answer retention option. Private files remain ignored and must not be staged or uploaded.

Before launch: verify subscription login, preview exactly eight arms, and run the relevant offline budget/privacy tests. Score correctness, instruction following and clarity independently (0–2 each), recording factual errors; absent owner scores remain absent, not inferred or supplied by Codex.

Status: all eight executions completed, zero failures, zero incomplete usage and zero tool calls. All eight result keys match the eight persistent reservations; this approval is now 8/8 exhausted. Codex version: `0.162.0-alpha.2`; execution fingerprint: `535fa4704fd29ec5a98c071366dbb665322cf54cda23f3ccbdecb600a0ebe022`.

Eight separate local answer artifacts and the A/B review page exist under the ignored private directory; the result JSONL contains zero answer-text fields. Human scores remain absent. The full local suite passes 334 tests, configured lint, secret scanning and whitespace validation. Hosted verification of this review-sink change remains pending. No savings, human quality or release acceptance is claimed. This document contains no participant identities or raw answers.
