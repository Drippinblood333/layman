# Cost, quality and routing benchmarks

## Static routing suite

`evals/router-v2/cases.jsonl` contains 300 varied cases across summary, rewrite, code explanation, debugging, architecture and extraction. Each category has 50 cases covering Chinese and English, long context, one versus multiple tools, previous-response state, budget/quality metadata, high-risk content and conflicting route overrides.

```powershell
.\.venv\Scripts\python evals\router-v2\run_eval.py
.\.venv\Scripts\python evals\router-v2\analyze_cases.py
```

The analyzer writes `results/routing-analysis.json` and reports confusion pairs, under/over-routing, route reasons and classification throughput.

## Real API calibration

Start the router with an API key, then run a small budget-capped calibration:

```powershell
.\.venv\Scripts\python evals\router-v2\benchmark.py --per-category 2 --max-cost-usd 1.00
```

The runner is resumable. For every selected case it calls `auto`, calls the configured deep model with the same output cap, and asks a blind deep-model judge to score both answers. It stores actual usage and price-table cost, latency, route, fallback and judge scores. `--no-judge` disables the third call.

The default sample is calibration evidence only. A release claim requires all 300 cases, human scoring, and the gates below:

- measured auto cost at least 20% below always-deep;
- automatic validator pass rate no more than 2 percentage points lower;
- human mean quality no more than 0.2/5 lower;
- zero high-risk routes below deep;
- fallback rate no more than 10%;
- privacy scan finds no raw production inputs or secrets.

Never present counterfactual dashboard savings as measured savings.

## ChatGPT Plus calibration without an API key

`layman codex-plus eval` is a separate, subscription-backed calibration path. Its dry run is the default and makes no model calls. The release checkpoint contains 18 self-contained cases from six task categories. Every case runs once with auto and once with the deep baseline, for 36 calls.

```powershell
layman codex-plus status
layman codex-plus eval
layman codex-plus eval --run
```

Safety properties:

- requires `codex login status` to report ChatGPT login and refuses API-key login;
- defaults to a hard 12-call cap and requires `--allow-more-calls` above it;
- runs ephemeral, isolated, read-only sessions and asks the model not to call tools;
- writes each completed arm immediately so an interrupted run resumes safely;
- does not retain prompt or answer text unless `--store-outputs` is explicitly supplied;
- stops early for subscription limits, authentication failures or unavailable models.

Codex-reported token counts and latency are measured. Any dollar comparison derived from the YAML API price table remains an estimate because ChatGPT subscription usage has no per-request API invoice. This path cannot validate Responses API streaming, proxy fallback or API error handling.

The prior exploratory Plus calibration is retained in the [`legacy-v2` archive](../archive/legacy-v2/docs/PLUS_CALIBRATION_2026-07-16.md). A fresh 18-case/36-call run is required for each release candidate; outputs remain local until manually reviewed and deliberately published.

## Direct execution versus Layman Auto

`evals/token_optimization` contains 30 synthetic repository tasks: six bug fixes, six features, five refactors, five testing tasks, four documentation/configuration tasks, and four high-risk read-only reviews. Each case runs from the same clean fixture in two randomized arms: direct Sol/medium and Layman context optimization plus automatic routing.

```powershell
.\.venv\Scripts\python evals\token_optimization\benchmark.py
.\.venv\Scripts\python evals\token_optimization\benchmark.py --run --max-calls 20
.\.venv\Scripts\python evals\token_optimization\benchmark.py --analyze
```

Run three 20-call batches for all 60 subscription calls. The harness stops on subscription/authentication errors or when cumulative execution failures exceed 10%. It saves hashes, route, model, effort, token counts, latency, tool/read metrics and hidden validation results, but not answer text or generated code.

Layman may claim Token savings only when all published gates pass: at least 15% paired median total-token reduction, positive bootstrap lower bound, no quality regression, safe high-risk routing, at least 20% output-token reduction, and no increase in median files read.

The 2026-07-16 accepted run completed all 30 pairs. Layman passed 30/30 hidden validations versus Direct's 29/30, but used 19.54% more total tokens at the paired median (95% interval: 3.24% to 26.75% more), produced 47.00% more output tokens and read a median of 8 files versus 5. The savings gate therefore failed. See the [full negative-result report](TOKEN_OPTIMIZATION_2026-07-16.md).
