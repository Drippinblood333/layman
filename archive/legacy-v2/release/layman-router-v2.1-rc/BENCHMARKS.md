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
