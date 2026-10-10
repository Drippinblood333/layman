# Approved eight-execution development trial

## Outcome: stopped at first validation failure

Executed on 2026-10-10 using Codex `0.162.0-alpha.2`. Persistent reservations:
**2/8 used, 6 unspent**. The process is terminal; no third execution was launched.
The unspent allowance is not permission to bypass the agreed first-failure stop.
Runtime fingerprint:
`e9976a6e7cb2fc606e43fce51dc5b4ff39747542d641f9cb21f8d36b2641d04a`.

| bugfix-02 metric | Direct | Layman |
| --- | ---: | ---: |
| Model / effort | gpt-6.1-sol / medium | gpt-6.1-sol / medium |
| CLI execution | Completed | Completed |
| Hidden function validation | Passed | **Failed** |
| Changed files | src/target.py | None |
| Tool calls / unique files read | 3 / 1 | 0 / 0 |
| Input tokens | 270,045 | 124,494 |
| Cached input (included above) | 248,960 | 110,336 |
| Uncached input | 21,085 | 14,158 |
| Output tokens | 1,062 | 580 |
| Total input + output | 271,107 | 125,074 |
| Latency milliseconds | 69,379 | 421,079 |

Both arms reported complete usage and no fallback. Layman returned a final
answer without performing the required edit, leaving the faulty implementation
unchanged. Scope containment passed but task quality did not. **This is not a
quality-equivalent token saving**; zero successful comparable pairs exist in this
batch. Do not pool this with older fingerprints or the four no-tools review
pairs. Exact reasons for the model's non-execution are not established by these
metadata; raw answers/events were not retained and must not be reconstructed.

The smallest next action is zero-model diagnosis of execution context and task
completion reporting, not a speculative contract rewrite or another paid/model
attempt. Resuming model trials after this stop requires an explicitly approved
follow-up protocol. Original reservations/results remain intact and private.
29 relevant offline harness tests and the zero-call route/order preview passed
before launch; no installer replacement, API billing, tag or release occurred.

## Predeclared protocol

### Subsequent zero-model instruction-loading check

Source `2340722c32b742774959330ae924df759a483407` passed all ten validation
jobs in [run 38050460774](https://github.com/Drippinblood333/layman/actions/runs/38050460774);
publication was skipped. The completion-reporting guard is hosted-verified,
not a runtime repair of model non-execution.

Official [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
describes `developer_instructions` as additional session instructions rather than
a replacement for built-in instructions. Native `codex debug prompt-input`
on version `0.162.0-alpha.2` was then used to render the unchanged bugfix-02
execution prompt with and without the current Layman contract, in a temporary
empty directory with subscription-safe environment. No model execution, user
configuration edit or raw-prompt retention occurred.

Both renderings contained five input items (three developer, two user) and kept
the explicit workspace-edit requirement. The Layman rendering contained the
complete current contract. JSON serialization lengths were 18,928 vs 19,727
characters (+799), not tokenizer counts or task savings. This rules out a missing
contract in this bounded rendering, not a historical root cause. The empty
directory and selected configuration overrides do not reconstruct the old
execution workspace, full tool schema, effective runtime permissions or model
behavior. Do not disable inherited safety rules or add stronger instructions
based on this inconclusive check. The trial remains stopped at 2/8 used.

Post-trial zero-model follow-up: mocked execution reproduced the success-label
gap. A bounded named-file/no-tools guard now reports `needs_verification` rather
than delivered success, with CLI/MCP failure signaling and no extra model call.
Seventy relevant offline tests pass. It does not explain why the trial model
declined tool use or prove that the model will now perform edits. Source changes
invalidate the old fingerprint; no runtime retest or trial resumption occurred.

The owner explicitly approved at most eight subscription model executions after
being told this means four paired development tasks, failures consume allowance,
and the first execution failure stops the batch. No paid API, installation
replacement or public release is approved. Earlier 12/36/8 journals stay intact.

Use the existing development benchmark, not the no-tools answer calibration.
Tasks perform real code edits and verification in isolated **synthetic** Git
repositories, not the owner's production code. Select before execution:

| Case | Development operation | Existing quality check |
| --- | --- | --- |
| bugfix-02 | Ordered deduplication | Hidden function checks and file scope |
| feature-02 | Pagination with invalid-argument handling | Hidden function checks and file scope |
| refactor-02 | Shared name-normalization helper | Hidden behavior checks and file scope |
| testing-02 | Tests for first-item/default behavior | Reference tests, mutation checks and file scope |

Two arms per task: direct Codex using configured balanced/medium, and current
Layman with one model attempt and current routing/contract. Confirm selected
Layman routes are balanced/medium before launch; actual model/effort is recorded.
Identical fixture, requested outcome and automated validation apply to each arm.
Layman's extra contract and any recovery overhead are part of its total usage.
Pair order uses fixed seed `20261010`; do not choose order from observed results.

Private output: `build/development-trial-2026-10-10-b8/results.jsonl` and its
adjacent persistent attempts journal; private work root is the same directory's
`work` subdirectory. Total cap is 8 across restarts and failures. Execute one arm
at a time (`max_calls=1`, `total_call_cap=8`), checking each recorded result before
the next launch. Stop on execution failure, failed validation, incomplete usage
or unexpected fallback. Never replace a failed attempt, steal a writer lock or
automatically replay an interrupted reservation. Existing harness removes only
its bounded synthetic workspaces after recording validation; no user files or
installation are changed. Result records exclude answer bodies and generated
code. Do not run a separate optimizer/model scorer.

Report input/output/cached/uncached tokens, success and validation outcomes,
latency and execution count; keep negative pairs. Existing analyzer gates remain
unchanged: four pairs cannot satisfy its 30-pair general-release savings gate.
This reused public fixture corpus is not a fresh holdout, independent human
review, broad real-project acceptance or a causal test of Ponytail alone. No
general savings claim follows from this small trial even if all checks pass.

Status before launch: approved, no reservations or executions yet. Subscription
login verified; relevant offline harness checks and zero-call route/order preview
must succeed before the first reservation.
