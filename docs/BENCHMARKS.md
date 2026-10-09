# Cost, quality and routing benchmarks

## Lossless repeated tool output (offline only)

The [RTK strategy](https://github.com/rtk-ai/rtk) of folding repeated log lines with counts informed an original reversible Python encoder; no upstream source or executable is bundled. Run the zero-call regression measurement with:

```powershell
.\.venv\Scripts\python evals\token_optimization\check_tool_output.py
```

Eight synthetic fixtures verify exact reconstruction and non-growth, including Chinese CRLF, a failure after repeated warnings, unique test output, short repetition, structured JSON, fenced code and a traceback. Repeated progress/warning/Chinese fixtures shrink from 2,905/2,735/2,929 UTF-8 bytes to 149/177/175 bytes; the other five fixtures stay unchanged. These are synthetic byte measurements, not tokenizer counts, live usage, task-quality results or bill savings. They cannot close the public token-savings gate.

API clients may explicitly set `metadata.layman_tool_output_mode="lossless_lines"` for automatic requests containing plain-text `function_call_output` logs. Routing safety classification happens before encoding. Current user instructions, tool arguments, call IDs and non-string outputs remain unchanged. Repetition counts and line order are preserved, and JSON/fenced code are not encoded. Every encoding includes reconstruction instructions; consumers requiring raw text should leave this off. The control metadata is stripped before upstream forwarding. Response headers expose mode/count, and local recent-usage reports expose byte counts without storing log text.

`layman compact-output` reads UTF-8 stdin and writes the encoded or unchanged text; `--restore` reconstructs the original. It executes no command and makes no model call. Windows binary stdin/stdout preserve CRLF and Unicode. A shell pipeline may mask the producer's failure status: retain and check that status separately; a successful filter does not verify the command that produced the log.

This feature does not automatically intercept Plus/Codex shell tools or shrink unrelated task history. Fresh paired end-to-end execution must measure whether tool-output reduction outweighs encoding overhead, re-reads and quality effects before publishing any total-token claim.

## Static routing suite

`evals/router-v2/cases.jsonl` contains 300 varied cases across summary, rewrite, code explanation, debugging, architecture and extraction. Each category has 50 cases covering Chinese and English, long context, one versus multiple tools, previous-response state, budget/quality metadata, high-risk content and conflicting route overrides.

```powershell
.\.venv\Scripts\python evals\router-v2\run_eval.py
.\.venv\Scripts\python evals\router-v2\analyze_cases.py
```

The analyzer writes `evals/router-v2/results/routing-analysis.json` and reports confusion pairs, under/over-routing, route reasons and classification throughput.

## Real API calibration

Start the router with an API key, then run a small budget-capped calibration:

```powershell
.\.venv\Scripts\python evals\router-v2\benchmark.py --per-category 2 --max-cost-usd 1.00
```

The runner supports only stateless cases without tools. It rejects fake `previous_response_id` values and tool cases before any paid call because those cases need real predecessor creation or a deterministic tool loop. Check a selection without an API key using `--validate-only`.

For every supported case it calls `auto`, calls the configured deep model with the same output cap, and asks a blind deep-model judge to score both answers. `--no-judge` disables the third call. Before each call it writes and flushes a conservative price-table reservation; after success it immediately writes a completion event. An interrupted in-flight reservation remains charged at its ceiling and blocks automatic continuation, preventing a rerun from silently duplicating a possibly billed call. The cap is a conservative price-table accounting limit, not an OpenAI invoice guarantee.

The experiment fingerprint covers the complete selected requests, local router configuration, live router health identity, upstream identity, normalized base URL, runner source, judge instructions/schema, output caps and requested `service_tier="default"`. The runner refuses non-official upstreams; it is specifically an OpenAI API calibration, not a generic compatible-proxy benchmark. Fallback, failed-validator, incomplete-service-tier and otherwise ineligible cases are excluded from the cost comparison instead of treating missing attempt usage as free. Stored costs are estimates computed from measured token usage and the versioned repository price table.

The default supported sample is calibration evidence only. The full 300-case corpus remains the deterministic routing gate; it is not a live quality run because it intentionally includes state and tool-routing fixtures. Any release-grade live quality claim requires a separately reviewed stateless/no-tool holdout, manual human scoring, and the gates below:

- price-table estimate from measured usage at least 20% below always-deep;
- automatic validator pass rate no more than 2 percentage points lower;
- human mean quality no more than 0.2/5 lower;
- zero high-risk routes below deep;
- fallback rate no more than 10%;
- privacy scan finds no raw production inputs or secrets.

The current runner does not yet import human scores or close these gates automatically, so API routing remains Beta. Never present counterfactual dashboard savings or price-table estimates as an API invoice or measured dollar savings.

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

The prior exploratory Plus calibration is retained in the [`legacy-v2` archive](../archive/legacy-v2/docs/PLUS_CALIBRATION_2026-07-16.md). A fresh 18-case/36-call run is required for each release candidate; each record is bound to the case corpus, resolved route plan, prompt protocol and verified Codex version by an experiment fingerprint. Outputs remain local until manually reviewed and deliberately published.

## Direct execution versus Layman Auto

### Bounded six-category pilot

After explicit subscription-use approval, `--pilot --max-calls 12 --total-call-cap 12` selects the first task from each category before execution, with two randomized arms per task. The direct baseline uses the configured balanced model at medium effort, matching the documented Sol/medium comparison; it no longer incorrectly reads the deep tier. Each arm has at most one Codex launch, without automatic model fallback. A persisted, flushed reservation journal counts failures and interrupted launches against the total authorization cap across restarts; incomplete reservations require review instead of silent replay. The pilot stops on execution failure, and incomplete usage is excluded from token comparisons rather than treated as free savings.

Here a "call" means one entire Codex task execution, which may contain multiple internal model/tool exchanges; it is not a hard cap on provider-internal requests. API-key billing is disabled. Six pairs cannot close the 30-pair public claim gate, and this Plus experiment does not exercise the new API-only tool-output encoding.

```powershell
.\.venv\Scripts\python -X utf8 evals\token_optimization\benchmark.py --pilot --max-calls 12 --total-call-cap 12 --seed 20261009 --output build/token-pilot-2026-10-09/results.jsonl --work-root build/token-pilot-2026-10-09/work
```

Preview is the default. Add `--run` only after approval. Use a fresh output file for a new authorization and experiment; never increase the cap or remove the reservation journal to bypass an existing approval ceiling. Machine-readable records contain fingerprints, counts and validation outcomes, not answer text or generated code.

For a bounded follow-up, preselect exact existing fixtures with repeatable `--case-id`, without `--pilot`. Unknown/duplicate IDs and conflicting selection modes are rejected before Codex resolution. Corpus order is canonical, the selected corpus is fingerprinted, and arms are randomized with the recorded seed. This option does not reset the shared reservation cap, bypass interrupted-attempt review or authorize model use. Like the pilot, it stops on the first execution failure. A subset is calibration evidence, not a fresh holdout or a way to close the 30-pair public gate; choose tasks before seeing outcomes and retain failures/negative results.

The remaining four approved attempts in the current trial are preselected for `feature-01` and `testing-01`, each with direct/Layman arms. This broadens task types beyond repeatedly testing `bugfix-01`; it does not constitute an untouched evaluation corpus. Zero-call preview, reusing the original journal/output:

```powershell
.\.venv\Scripts\python -X utf8 evals\token_optimization\benchmark.py --case-id feature-01 --case-id testing-01 --max-calls 4 --total-call-cap 12 --seed 20261010 --output build/token-pilot-2026-10-09/results.jsonl --work-root build/token-pilot-2026-10-09/work
```

`evals/token_optimization` contains 30 synthetic repository tasks: six bug fixes, six features, five refactors, five testing tasks, four documentation/configuration tasks, and four high-risk read-only reviews. Each case runs from the same clean fixture in two randomized arms: direct Sol/medium and Layman context optimization plus automatic routing.

```powershell
.\.venv\Scripts\python evals\token_optimization\benchmark.py
.\.venv\Scripts\python evals\token_optimization\benchmark.py --run --max-calls 20
.\.venv\Scripts\python evals\token_optimization\benchmark.py --analyze
```

Run three 20-call batches for all 60 subscription calls. The harness stops on subscription/authentication errors or when cumulative execution failures exceed 10%. It saves hashes, route, model, effort, token counts, latency, tool/read metrics and hidden validation results, but not answer text or generated code.

Every record also carries a UTC timestamp and an experiment fingerprint over the case corpus, routing configuration, execution policy, execution/compaction prompts, randomization seed, fixture/validator protocol and actual Codex CLI version. Resume logic and analysis only reuse records with the same fingerprint, so a policy or runtime change cannot silently inherit an older result. A changed fingerprint requires a new 60-call run; use a fresh holdout before turning that calibration into a public product claim.

Layman may claim Token savings only when all published gates pass: at least 15% paired median total-token reduction, positive bootstrap lower bound, no quality regression, safe high-risk routing, at least 20% output-token reduction, and no increase in median files read.

The 2026-07-16 accepted run completed all 30 pairs. Layman passed 30/30 hidden validations versus Direct's 29/30, but used 19.54% more total tokens at the paired median (95% interval: 3.24% to 26.75% more), produced 47.00% more output tokens and read a median of 8 files versus 5. The savings gate therefore failed. See the [full negative-result report](TOKEN_OPTIMIZATION_2026-07-16.md).

The leaner policy was tried in the [2026-10-09 bounded subscription pilot](TOKEN_PILOT_2026-10-09.md): one Layman execution passed, but the direct baseline failed immediately with incomplete usage. Two of the twelve authorized attempts were used. There are no usable new pairs and no new savings claim; the negative 2026-07-16 result remains the latest complete paired comparison.
