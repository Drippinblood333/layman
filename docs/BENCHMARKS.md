# Cost, quality and routing benchmarks

## Deferred tool discovery (API compatibility only)

The official [tool-search guide](https://developers.openai.com/api/docs/guides/tools-tool-search)
describes loading tool definitions on demand. A Responses client must include a
`tool_search` tool and set `defer_loading: true` on selected functions (including
functions inside a namespace) or an MCP server. This is not a flag that defers
every tool automatically. Names/descriptions still have context overhead, discovery
adds work, and live quality/input-token/latency comparisons remain necessary.

Layman does not add these fields, regroup tools, disable capabilities, remove
approval requirements or execute a discovery loop for the caller. Three mocked
transport cases verify that its existing API proxy preserves mixed eager/deferred
namespace definitions, deferred MCP settings and approvals, tool choice, JSON/SSE
responses, and client `tool_search_call`/`tool_search_output` history. The client
case also preserves `additional_tools` position and `previous_response_id` when
the existing optional context/log encoders are enabled. Schema markers stay out
of local telemetry. These are local compatibility checks, not upstream schema
acceptance, real discovery success, or measured token savings.

Do not confuse this API surface with Plus CLI feature flags. On the privately
tested `codex-cli 0.162.0-alpha.20`, `code_mode_tool_search` and `incremental_tools`
are under development/false; `tool_search` is marked removed. No such flags or
global configuration were changed. This version-specific inspection does not
establish a stable Plus default or justify hiding the user's tool catalog.

## Subscription command-output diagnostics

The streamed Layman runner and buffered Direct runner expose two additive numeric
fields: `command_output_chars` (Unicode characters in native completed command
items' string `aggregated_output`) and `command_outputs_observed` (number of such
outputs, including empty strings). Repeated completed items with the same nonempty
string command ID count once. Items without usable IDs cannot be deduplicated.
Started/updated items, nested tool results, assistant text and non-string or absent
outputs are excluded. Only lengths and counts are returned; no output text or
command arguments are added to records. Both fields also propagate through Layman
attempts and synthetic benchmark records.

These fields help investigate large tool results, not measure per-request token
growth. Zero observed outputs means no size coverage, not proof of no output.
Older records without these fields are unknown, not zero. CLI output may already
be truncated; MCP/file/search outputs and internal model requests are not covered.
The official [JSONL event contract](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)
provides completed-turn usage; do not infer a per-model-request usage trace from
tool counts or output characters. No savings claim follows from these diagnostics.

## Lossless repeated tool output (offline only)

The [RTK strategy](https://github.com/rtk-ai/rtk) of folding repeated log lines with counts informed an original reversible Python encoder; no upstream source or executable is bundled. Run the zero-call regression measurement with:

```powershell
.\.venv\Scripts\python evals\token_optimization\check_tool_output.py
```

Eight synthetic fixtures verify exact reconstruction and non-growth, including Chinese CRLF, a failure after repeated warnings, unique test output, short repetition, structured JSON, fenced code and a traceback. Repeated progress/warning/Chinese fixtures shrink from 2,905/2,735/2,929 UTF-8 bytes to 149/177/175 bytes; the other five fixtures stay unchanged. These are synthetic byte measurements, not tokenizer counts, live usage, task-quality results or bill savings. They cannot close the public token-savings gate.

API clients may explicitly set `metadata.layman_tool_output_mode="lossless_lines"` for automatic requests containing plain-text `function_call_output` logs. Routing safety classification happens before encoding. Current user instructions, tool arguments, call IDs and non-string outputs remain unchanged. Repetition counts and line order are preserved, and JSON/fenced code are not encoded. Every encoding includes reconstruction instructions; consumers requiring raw text should leave this off. The control metadata is stripped before upstream forwarding. Response headers expose mode/count, and local recent-usage reports expose byte counts without storing log text.

`layman compact-output` reads UTF-8 stdin and writes the encoded or unchanged text; `--restore` reconstructs the original. It executes no command and makes no model call. Windows binary stdin/stdout preserve CRLF and Unicode. A shell pipeline may mask the producer's failure status: retain and check that status separately; a successful filter does not verify the command that produced the log.

This feature does not automatically intercept Plus/Codex shell tools or shrink unrelated task history. Fresh paired end-to-end execution must measure whether tool-output reduction outweighs encoding overhead, re-reads and quality effects before publishing any total-token claim.

The [v2 synthetic CLI log-extraction pilot](LOSSLESS_LOG_PILOT_V2_2026-10-18.md) completed its separate two-invocation ceiling: raw 37,301 total tokens / strict answer PASS; encoded 21,345 / strict answer FAIL. Both had complete usage, zero tools and no cached tokens. The lower encoded usage is **not an accepted same-quality saving**. Per-field failure details were not retained, so no specific model misreading is established. This is neither an API transport test nor a coding-quality benchmark; encoding remains experimental and opt-in.

The [separate v3 diagnostic](LOSSLESS_LOG_DIAGNOSTIC_V3_2026-10-18.md) reused that exact task and gate with value-free per-field checks: raw passed all six; encoded parsed and matched schema but failed marker equality (the other five matched). Total usage 37,397/21,513 is again not accepted savings. High cache reuse and this reused synthetic case are disclosed; missing answer values prevent diagnosing whitespace versus other content. No automatic normalization or default change was made.

Future synthetic tasks have a public [line-content contract](../evals/token_optimization/log_contract.py): exclude only CRLF/LF/CR terminators, preserve all other spaces/tabs. Independent offline reference checks cover three new fixtures and reject trimming or retained terminators. These are public validation cases, not holdouts, model-quality results or retroactive changes to v1-v3 scoring.

A [separate independent two-task feasibility pilot](INDEPENDENT_LOG_CONTRACT_PILOT_2026-10-18.md) then completed its frozen four-invocation cap: both raw/encoded pairs passed all six exact fields, with summed native totals 51,326 versus 42,854 (16.51% lower). This observed reduction applies only to those clarified synthetic extraction tasks. Cache was unequal, one encoded arm was slower, and earlier failures remain; it is not general coding, billing, transport or release-grade evidence. Defaults stay unchanged.

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

The [2026-10-09 protocol-v4 calibration](PLUS_CALIBRATION_2026-10-09.md) completed all 36 approved executions with complete usage and no tool calls/failures. Auto total tokens were 1.70% higher than the always-deep baseline; human scores are absent. This is complete execution coverage, not quality acceptance or a public savings result. `--total-call-cap` now persists pre-launch reservations across batches/fingerprints, counts failures, refuses interrupted-reservation replay and uses an exclusive writer lock. Existing locks are not automatically stolen. The approved 36-execution journal is exhausted; further evaluation requires new explicit authorization. Per-batch `--max-calls` alone is not a cumulative approval ceiling.

Capped execution also refuses historical result rows without matching reservations, including partial journals and duplicate rows. It checks multiplicity across all fingerprints, not just completed keys in the current plan. A legacy result file cannot silently become a zero-used authorization journal; review its actual history before an explicitly authorized migration. The runner does not synthesize reservations, reset results or consume another model call to repair ambiguous accounting.

## Direct execution versus Layman Auto

### Bounded six-category pilot

After explicit subscription-use approval, `--pilot --max-calls 12 --total-call-cap 12` selects the first task from each category before execution, with two randomized arms per task. The direct baseline uses the configured balanced model at medium effort, matching the documented Sol/medium comparison; it no longer incorrectly reads the deep tier. Each arm has at most one Codex launch, without automatic model fallback. A persisted, flushed reservation journal counts failures and interrupted launches against the total authorization cap across restarts; incomplete reservations require review instead of silent replay. The pilot stops on execution failure, and incomplete usage is excluded from token comparisons rather than treated as free savings.

Here a "call" means one entire Codex task execution, which may contain multiple internal model/tool exchanges; it is not a hard cap on provider-internal requests. API-key billing is disabled. Six pairs cannot close the 30-pair public claim gate, and this Plus experiment does not exercise the new API-only tool-output encoding.

Executing the local task benchmark now requires an exclusive `<output>.lock` before login or reservation reads. A concurrent writer targeting the same resolved output fails before reaching Codex; budget reads, reservations and result writes occur under one writer's lock. Normal completion/exceptions remove only that writer's owned lock. A crashed process can leave a stale lock: verify the actual process and journal before requesting recovery, never delete a lock or replay reservations automatically. Preview remains lock-free. This protects this local runner's shared journal, not other output paths, independent API tools, provider-internal requests or distributed/network filesystems. It does not expand authorization.

```powershell
.\.venv\Scripts\python -X utf8 evals\token_optimization\benchmark.py --pilot --max-calls 12 --total-call-cap 12 --seed 20261009 --output build/token-pilot-2026-10-09/results.jsonl --work-root build/token-pilot-2026-10-09/work
```

Preview is the default. Add `--run` only after approval. Use a fresh output file for a new authorization and experiment; never increase the cap or remove the reservation journal to bypass an existing approval ceiling. Machine-readable records contain fingerprints, counts and validation outcomes, not answer text or generated code.

For a bounded follow-up, preselect exact existing fixtures with repeatable `--case-id`, without `--pilot`. Unknown/duplicate IDs and conflicting selection modes are rejected before Codex resolution. Corpus order is canonical, the selected corpus is fingerprinted, and arms are randomized with the recorded seed. This option does not reset the shared reservation cap, bypass interrupted-attempt review or authorize model use. Like the pilot, it stops on the first execution failure. A subset is calibration evidence, not a fresh holdout or a way to close the 30-pair public gate; choose tasks before seeing outcomes and retain failures/negative results.

The final four approved attempts in the current trial were preselected for `feature-01` and `testing-01`, each with direct/Layman arms. They have now completed: total-token reductions were 8.18% and 11.32%, but output and elapsed time increased, and the public claim gate remains false. The original trial is exhausted at 12/12; do not add `--run` under a different journal or raised cap to bypass it. See the [complete evidence and limitations](TOKEN_PILOT_2026-10-09.md#ninth-through-twelfth-attempts-preselected-feature-and-testing-pairs). This broadens calibration task types beyond repeatedly testing `bugfix-01`; it does not constitute an untouched evaluation corpus. Zero-call preview, reusing the original journal/output:

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
