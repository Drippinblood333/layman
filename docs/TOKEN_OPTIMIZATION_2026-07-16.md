# ChatGPT Plus token-optimization calibration — 2026-07-16

## Outcome

The Experimental Layman Auto path did **not** save tokens in this calibration and must not be advertised as doing so.

| Metric | Direct Sol/medium | Layman Auto | Result |
|---|---:|---:|---:|
| Hidden validation success | 29/30 | 30/30 | Layman +1 task |
| Median reported input tokens | 106,503.5 | 133,125 | Layman higher |
| Median reported output tokens | 1,008 | 1,450.5 | Layman higher |
| Paired median total-token change | — | +19.54% | savings gate failed |
| Bootstrap 95% interval for total-token change | — | +3.24% to +26.75% | increase is consistently positive |
| Paired median output-token change | — | +47.00% | savings gate failed |
| Median unique files read | 5 | 8 | file gate failed |
| Median latency | 56.49 s | 67.06 s | Layman slower |
| Median tool calls | 6 | 8 | Layman used more tools |

All 60 accepted arms completed without an execution failure. No arm modified a file outside its allowed paths. All four high-risk Layman arms used Deep, Sol/high and a read-only sandbox and passed their safety checks. No benchmark task reached the compaction threshold.

Layman selected Balanced for 20 tasks and Deep for 10; it selected Fast for none. That routing mix, together with more file reads and tool calls, is a likely contributor to the token increase, but this is an inference rather than a separately controlled causal result.

## Method

- 30 synthetic repository tasks: 6 bug fixes, 6 features, 5 refactors, 5 testing tasks, 4 documentation/configuration tasks and 4 high-risk read-only reviews.
- Two randomized arms from clean Git fixtures: Direct uses Sol/medium; Layman uses automatic routing plus its context-efficiency contract.
- Token counts and latency come from Codex JSON events. Total tokens are reported input plus output tokens; cached input is not added a second time.
- Function tasks use hidden behavior checks. Test-writing tasks use mutation testing. Content tasks check explicit requested content. High-risk tasks check required plan terms and zero file changes.
- Results retain metrics and hashes, not prompt text, generated code or answer text. The prompts themselves are versioned synthetic fixtures in `evals/token_optimization/cases.py`.

During calibration, ambiguous synthetic specifications and syntax-dependent validators were found, corrected and their affected attempts archived outside the accepted result set. The final analysis contains exactly one accepted Direct and one accepted Layman record for each of the 30 tasks. These extra diagnostic/replacement attempts mean subscription usage was greater than the 60 accepted calls; they are not included in the reported comparison.

## Release decision

The published savings gate failed. Token optimization remains **Experimental** and API context rewriting remains opt-in. The release must state this negative result and must not claim a fixed token-saving percentage or actual API-bill savings.

The next experiment should focus on why no task selected Fast, reduce redundant tool/file access, and validate compaction separately with genuinely long-history tasks. Any tuned policy should be evaluated on a new holdout set rather than reusing these 30 tasks as proof.
