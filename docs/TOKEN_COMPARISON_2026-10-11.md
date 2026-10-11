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

## Broader coverage paused on a weak validation criterion

A subsequent preselected eight-call set covered bugfix-04, feature-04,
refactor-02 and testing-03. It paused after four calls, before the latter two
categories, when offline review found bugfix-04's hidden checks did not cover
the requested negative size. Its original buggy source already passed the old
checks. The generated model sources had been cleaned up, so historical negative-
size correctness cannot be recovered; neither bugfix-04 arm is evidence of
equivalent successful delivery. Do not retrospectively rewrite those raw records.

Private token-coverage-2026-10-11 journal/results retain four calls. Legacy totals:
bugfix-04 Direct 281375, Layman 253763; feature-04 Direct 266650, Layman 239812.
All native turns completed with complete usage and no fallback, but native
completion/usage cannot repair the weak bugfix quality gate. No aggregate savings
claim follows. Fingerprint:
8d7362de5d50c9334d2c88af390380f49ff520d9141a39332e64f810ad980f78.

The hidden criterion now includes zero and negative sizes, including negative
size on empty input. The new regression rejected the original validator before
the fix; the full 51-case benchmark test suite passes afterward, including all
17 function tasks rejecting their original broken source. No model call was
needed to establish this defect. Other criteria/prompts remain unchanged.

The remaining four calls of that eight-call allowance are re-scoped, before
execution, to revalidate bugfix-04 with its repaired criterion and compare the
previously untested refactor-02. A separate four-call journal avoids replay and
pooling across the changed case fingerprint; original four plus new four is
still eight, not a replenished unlimited allowance. Testing-03 coverage remains
pending. No change to runtime model policy, permissions, installation or release.

Outcome: the repaired-criterion comparison stopped after two calls. Direct
passed (208053 total tokens); Layman used zero tool actions, changed no files,
failed hidden checks and correctly returned needs_verification (70808 tokens).
Fingerprint 0ecc44ac8d555dce730f04656705d6666f4c9a1d2a1c449326b4d8420f8f53e2.
This negative pair is excluded from reduction estimates. Refactor-02 remains
unexecuted. The two remaining calls were explicitly re-scoped after review to
fault observation, not blind retry or a replacement positive comparison.

First observation again used zero tools, failed artifact checks and returned
needs_verification (76999 tokens); two agent messages matched none of the fixed
answer-reported blocker categories. Raw text was not retained, so the nonexecution
rationale remains unknown. Extended observation added fixed completion/code
categories and allowlisted completed-item type counts; that call executed three
actions and passed the repaired checks (153184 tokens), with a completion claim,
two MCP calls and one file change. Two additional item kinds remained unknown.
Neither observation saw an EPERM marker. No runtime contract changed between
these calls; success after failures contradicts a deterministic repair claim.

Private nonexecution-result.json / nonexecution-extended-result.json fingerprints:
3d9daa217e5a034c4d9ba5d487ed6af85a193efbbcd69afdb12a808aa251539f;
a188dd5154b028efac8e0c0f2d1662f2cc6dce5c0aca426380e9424e8f1aeeb8.
The broad-coverage allowance is now 8/8 (four legacy, two repaired comparisons,
two observations), not four successful pairs. The three Layman calls on the
same task consumed 300991 tokens in total, including fault diagnosis; do not
advertise only the final successful 153184-token call as equivalent delivery
savings against the 208053-token Direct run. This was diagnosis, not a controlled
automatic-retry experiment; do not pool its fingerprints into aggregate savings.

Zero-model app-server schema export exposes additional item variants, including
functionCallOutput, dynamicToolCall and collabAgentToolCall. It does not establish
the unknown CLI item types or explain earlier failure turns. Do not alter native
event accounting based only on hypothetical correspondence between APIs.

## Private stable-CLI compatibility screen

Registry metadata reported @openai/codex 0.162.1. A project-private, ignored build
directory installed that exact resolved version with lifecycle scripts disabled;
it is not part of Layman's package and did not replace the existing installation
or global config. Version/startup and ChatGPT-login checks succeeded before model
calls. Native executable SHA256:
dd13bdb162a184fa04039488b234a8258ef9b76f84e926c505d5742b19249a6a.

A separate two-call comparison of repaired bugfix-04 passed both arms: Direct
255437 total tokens, Layman 228623, four tool actions each, complete usage, no
fallback. Fingerprint:
f8f79303cc9a28eb11223b19f77227ec7543343eef79b4aecf9712d3cb5fcb02.
One pair/version screen cannot establish that the alpha version caused failures,
that stable eliminates them, or that general token savings exist. Do not pool it
with the alpha-version records or silently change the default resolved binary.

Two preselected stable-only delivery observations then passed refactor-02 and
testing-03 independent function/mutation and scope checks: 213055 and 268038 total
tokens, four and five actions respectively, only allowed files changed, complete
usage/no fallback. This is reliability coverage, not a Direct comparison.
Fingerprint:
035ec3c8fb637d6583a43c03b07b2131254942545a2bc75260bf496d284731f3.
Each trace included two unknown completed-item types even after adding known
app-server enum mappings. Their actual types are not established; no speculative
event-accounting change follows. No failure-body review was needed in these two
calls. Private synthetic review, if a future check fails, may appear in this
Codex diagnostic chat but is not persisted in Layman aggregate telemetry.

The official [config basics](https://learn.chatgpt.com/docs/config-file/config-basic)
documents unified_exec as enabled except on Windows. Effective local alpha/stable
feature inspection showed unified_exec and unified_exec_tty enabled, and prior
zero-model Windows streaming/PTY rejection evidence exists. This is a concrete
compatibility hypothesis, not established causality for zero-tool turns. A new
two-call alpha-CLI observation restores only unified_exec=false for each child
invocation, with the existing model/effort, sandbox and approval settings intact.
No global flag, install, MCP service or permission changes. Its preselected tasks
are repaired bugfix-04 and refactor-02, stopping on first delivery failure.
