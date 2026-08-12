# ChatGPT Plus release calibration — Layman 1.0.0

Date: 2026-07-16

## Method

The release checkpoint contains 18 synthetic cases from six categories. Each case ran once with the auto-selected model/effort and once with the always-deep baseline, for 36 ChatGPT-authenticated Codex tasks. The evaluator removed API-key and custom-endpoint environment variables, used ephemeral read-only sessions, and stored no prompt or answer text.

All 36 tasks completed successfully. Auto selected 3 fast, 5 balanced and 10 deep routes. No record contains `answer_text`.

## Results

| Metric | Auto | Always deep | Difference |
|---|---:|---:|---:|
| Calls completed | 18/18 | 18/18 | none |
| Total latency | 300.849 s | 262.901 s | auto 14.43% higher |
| Input tokens | 232,624 | 227,378 | auto 2.31% higher |
| Cached input tokens | 174,592 | 185,856 | auto 6.06% lower |
| Uncached input tokens | 58,032 | 41,522 | auto 39.76% higher |
| Output tokens | 5,750 | 5,355 | auto 7.38% higher |
| API-price-table equivalent | $0.434505 | $0.461188 | auto 5.79% lower |

## Interpretation

This run validates the fixed 36-call subscription workflow, route execution and privacy defaults. It does not demonstrate lower latency or lower token usage. The 5.79% dollar difference is a counterfactual estimate from the repository price table, not an API invoice, because the run used ChatGPT subscription authentication.

Answer text was intentionally not retained, so semantic correctness and instruction-following could not receive human scores after execution. Completion status, hashes and character counts are not substitutes for quality review. The release quality gate therefore remains open until invited testers review outputs during an explicitly output-retaining synthetic run or score responses live.

No fixed token-saving or measured monetary-saving claim is supported by this calibration.
