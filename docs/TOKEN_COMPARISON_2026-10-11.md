# Bounded equivalent-delivery token comparison

Date: 2026-10-11. Owner authorized discretionary diagnostic ceilings and continued
use of the current subscription five-hour window. This batch selected four calls,
one attempt per arm, without API billing, permission expansion, installation or
release. Historical exhausted journals were not changed. Native Codex
0.162.0-alpha.2; both arms use configured balanced GPT-6.1 Sol / medium. Existing
bugfix-03 and feature-03 prompts, fixtures and independent quality/scope checks
were unchanged. Seed 20261011 ordered Direct then Layman for both tasks; shared
cache/order effects and small synthetic fixtures limit generalization.

Before execution, three offline regression failures reproduced an evaluation
defect: bounded selections continued after artifact-quality failure when native
execution completed, and token-reduction estimates admitted quality-failed pairs.
The runner now stops such bounded failures; estimates require both arms to pass.
Failure outcomes remain in pair/success counts. Usage eligibility and quality
eligibility are separate fields. All 32 benchmark tests and changed-file Ruff/
diff checks passed. This changes evaluation gates, not the runtime model policy.

Private evidence: build/token-comparison-2026-10-11/results.jsonl and its fsynced
attempt journal. Four reservations, four terminal results, no retry. JSONL stores
hashes and aggregate metrics, not prompt/answer/code bodies. All four usage records
are complete, with no fallback or compaction. Each changed only src/target.py and
passed external hidden function checks and scope checks.

| Task / arm | Input | Cached input | Uncached input | Output | Total | Tool actions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bugfix-03 / Direct | 271974 | 250112 | 21862 | 1584 | 273558 | 4 |
| bugfix-03 / Layman | 239710 | 222592 | 17118 | 1429 | 241139 | 4 |
| feature-03 / Direct | 271546 | 250112 | 21434 | 1438 | 272984 | 5 |
| feature-03 / Layman | 211222 | 194432 | 16790 | 1493 | 212715 | 4 |

Observed total reductions: bugfix-03 11.85%, feature-03 22.08%; two-pair median
16.96%. Median output reduction is only 2.98%, and feature-03 output increased.
These are observed task-pair measurements, not general Layman savings, API cost,
subscription-limit savings or causal attribution to one instruction. The native
event format reports usage separately from execution items; see
[official non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode).
Do not infer dollar cost from cached/uncached counts for a subscription run.

Analysis reports two usage-eligible and quality-eligible pairs, both arms 2/2
successful, claim_token_savings=false. Thirty-pair coverage and output-reduction
gates are not met. The two-sample bootstrap calculation is not representative
population evidence. Negative older trials remain valid historical evidence and
must not be pooled across different source/contract fingerprints.

Execution fingerprint:
fd340c2efc7e571b3502269d5a609a8e3a97f7fb286880f6c218ac380236046a.

Next: broaden preselected task categories under a fixed fingerprint and quality
criteria; investigate whole-task waste if benefits fail to generalize. Do not
rerun these passing pairs just to consume the remaining subscription allowance.
