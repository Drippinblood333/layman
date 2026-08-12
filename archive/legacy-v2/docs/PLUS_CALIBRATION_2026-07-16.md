# ChatGPT Plus calibration — 2026-07-16

## Scope

This calibration used the ChatGPT-authenticated Codex CLI through `layman-router codex-plus eval --run --store-outputs`. `codex login status` reported `Logged in using ChatGPT`, and `--ignore-user-config` selected the default ChatGPT-backed provider rather than the Layman API provider. Seventy synthetic cases were run with auto; a stratified subset of 34 also ran with the always-deep baseline, for 104 completed Codex tasks. The evaluator strips API-key and custom API-endpoint environment variables from child processes.

This is a small product calibration, not the 300-case release benchmark. ChatGPT subscription consumption is not exposed as a per-request dollar charge, so this report does not claim measured monetary savings.

## Result

| Metric | Auto | Always deep | Difference |
|---|---:|---:|---:|
| Completed paired tasks | 34 | 34 | 0 failures |
| Total paired latency | 448.903 s | 511.765 s | auto 12.28% lower |
| Mean paired latency | 13.203 s | 15.052 s | auto 1.849 s lower |
| Paired input tokens | 423,800 | 430,860 | auto 1.64% lower |
| Paired cached input tokens | 293,376 | 311,040 | auto 5.68% lower |
| Paired uncached input tokens | 130,424 | 119,820 | auto 8.85% higher |
| Paired output tokens | 6,325 | 6,821 | auto 7.27% lower |
| Deterministic quality checks | 70/70 | 34/34 | all 104 answers passed |

Across all 70 auto cases, routing selected 15 fast, 21 balanced and 34 deep. The paired subset intentionally emphasizes routes below deep, so paired results must not be presented as an unbiased estimate for the full workload. The uncached-token reversal at this checkpoint also shows that independent Codex runs have volatile cache states. Routing to a cheaper model does not guarantee lower latency or shorter visible output on every request.

Within the 34 measured pairs, applying the repository YAML API price table gives an **estimated** API-equivalent cost of `$0.585029` for auto versus `$0.959250` for always-deep, a 39.01% difference. To reduce selection bias, a separate 70-case counterfactual uses measured deep responses where available and reprices unpaired observed tokens at the deep rate; that estimate is `$1.454554` for auto versus `$1.941138` for always-deep, a 25.07% difference. Both are estimates only; this run used ChatGPT subscription authentication and did not measure an API invoice.

## Quality review

All 104 answers passed task-specific checks:

- summaries retained the required figures, facts and conclusions within the requested bullet limits;
- rewrites preserved all constraints and stayed within their requested length limits;
- code explanations correctly covered deduplication, optional chaining and token-signature verification;
- debugging answers correctly fixed dictionary mutation, JavaScript closure binding and the SQL `LEFT JOIN` filter;
- architecture answers covered consistency, scope control, degradation and measurable evolution criteria;
- extraction answers returned valid JSON with the exact requested values and ordering.

Manual inspection found no material correctness or instruction-following regression in auto. Thirty-four auto cases used deep/high, so their comparison-arm differences reflect normal sampling rather than routing savings.

## Interpretation and next step

Each isolated Codex execution carried roughly 11.4K–12.7K input tokens even for a short prompt because Codex supplies its own agent context. This makes a 600-call Plus comparison wasteful. Keep the 300-case suite offline, and use Plus only for small stratified quality samples.

This 70-case checkpoint validates the Plus workflow, selective baseline sampling and a broader set of boundary routes, but it is still not the final 100-case claim. The remaining checkpoint is 100 cases, planned as 30 more auto cases plus 6 stratified deep baselines. Before continuing, observe the account's reset behavior; do not infer measured monetary savings from this checkpoint.
