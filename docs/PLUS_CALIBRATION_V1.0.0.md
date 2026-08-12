# Historical ChatGPT Plus calibration — Layman pre-1.0

Date: 2026-07-16

## Method

This historical checkpoint contains 18 synthetic cases from six categories. Each case ran once with the auto-selected model/effort and once with the always-deep baseline, for 36 ChatGPT-authenticated Codex tasks. The evaluator removed API-key and custom-endpoint environment variables, used ephemeral read-only sessions, and stored no prompt or answer text. These records predate the release-candidate experiment fingerprint and cannot close a later candidate's calibration gate.

All 36 calls completed without an execution error. Auto selected 3 fast, 5 balanced and 10 deep routes. No record contains `answer_text`; semantic success was not scored.

## Results

| Metric | Auto | Always deep | Difference |
|---|---:|---:|---:|
| Calls completed | 18/18 | 18/18 | none |
| Total latency | 300.849 s | 262.901 s | auto 14.43% higher |
| Input tokens | 232,624 | 227,378 | auto 2.31% higher |
| Cached input tokens | 174,592 | 185,856 | auto 6.06% lower |
| Uncached input tokens | 58,032 | 41,522 | auto 39.76% higher |
| Output tokens | 5,750 | 5,355 | auto 7.38% higher |
| Re-priced API equivalent | $0.411415 | $0.461188 | auto 10.79% lower |

## Interpretation

This run historically validated the fixed 36-call subscription workflow, route execution and privacy defaults. It does not demonstrate lower latency or lower token usage. The 10.79% dollar difference is a counterfactual re-pricing of measured usage under `openai-standard-2026-07-30`, not an API invoice, because the run used ChatGPT subscription authentication. It does not reproduce the price assumptions used on 2026-07-16 and is not current release evidence.

Answer text was intentionally not retained, so semantic correctness and instruction-following could not receive human scores after execution. Completion status, hashes and character counts are not substitutes for quality review. The release quality gate therefore remains open until invited testers review outputs during an explicitly output-retaining synthetic run or score responses live.

No fixed token-saving or measured monetary-saving claim is supported by this calibration.
