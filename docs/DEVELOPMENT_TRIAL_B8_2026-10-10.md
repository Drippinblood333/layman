# Approved eight-execution development trial

## 2026-10-11 authorized final four executions (predeclared)

The owner approved starting the previously proposed remaining four subscription
executions. This batch uses current source at `ee39cd1` (runtime/source changes
through `dc6e76d`), a fresh fingerprint and separate private `current-results.jsonl`.
The original append-only attempts journal remains authoritative: 4/8 used before
launch, maximum 8/8 including failed or interrupted attempts. No paid API,
installation replacement, release/tag or automatic retry is included.

Predeclared fixed order: `feature-02:direct`, `feature-02:layman`,
`testing-02:layman`, `testing-02:direct`. Both arms use configured balanced model
and medium reasoning, one attempt each. These are existing synthetic fixtures,
not fresh holdouts. Pagination uses hidden function and file-scope checks;
testing uses reference tests, three mutation checks and file scope. Each result
must complete, pass validation, report complete usage and avoid fallback before
the next arm starts. First failure stops the entire batch; no replacement call.
The wrapper holds the original writer lock and fsyncs a reservation before launch.
Results exclude answer bodies/generated code; temporary fixtures are removed
after validation. A zero-call route preview and relevant offline harness tests
precede execution. Small-sample paired results do not establish general savings.

Status: stopped after the first pair; the Layman arm failed functional validation.
No testing-02 arm was launched and no retry occurred. Original journal now has
6/8 reservations, leaving two unused; this stopped batch is not automatically
resumed. Native version was `codex-cli 0.162.0-alpha.2`; both arms used
`gpt-6.1-sol` / medium. Current experiment fingerprint:
`d17ef83c8024df5acb04c6b703eb510df4c4118143b9f5d0d247af60293d3322`.
The 29 relevant offline harness tests and both zero-call route previews passed.

| feature-02 arm | Input | Cached input | Uncached input | Output | Total | Latency | Tools | Validation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Direct | 291026 | 267264 | 23762 | 1559 | 292585 | 41020 ms | 4 | Function/scope passed; only src/target.py changed |
| Layman | 151952 | 136832 | 15120 | 1101 | 153053 | 36492 ms | 0 | Function failed; no files changed, scope passed |

Usage was complete and neither arm used fallback. Native Layman execution
reported a completed process, but the delivery guard correctly converted the
public status to `needs_verification` / `workspace_execution_not_observed`.
Thus current guard behavior is runtime-confirmed for this case; actual execution
reliability remains unresolved. Lower usage on the failed arm is **not token
savings**. This is one failed pair, not a quality-equivalent efficiency result.
No answer body or generated code was retained in result records; temporary
synthetic fixtures were removed after validation. The model's exact reason for
omitting tools is not established by these records; do not attribute it to one
contract sentence, sandbox defect or configuration without additional evidence.

## Zero-model sandbox startup check

2026-10-11 transport follow-up: source inspection confirms both direct and
streamed execution pass `-` for stdin, set workspace cwd, UTF-8 text mode and
the workspace permission profile. The official
[CLI reference](https://learn.chatgpt.com/docs/cli/reference) documents stdin
prompt and cwd/config overrides; it does not establish why the model omitted
tools. Two new real-child regression cases (no model or login) confirm identical
expected UTF-8 pipe payloads and cwd for direct vs streamed execution: a Chinese
pagination request and multiline Unicode/quoted content in a Unicode/spaced
workspace. The child consumes stdin through EOF and emits synthetic usage.
All 47 tests in `test_plus_run.py` pass locally. Windows text-mode newline
translation applies to both paths; these tests deliberately check the platform
mapping and do not claim original line-ending bytes are preserved. They neither
reproduce the failed native model execution nor rule out all transport races,
effective tool availability, contract influence or model behavior. No runtime
contract/configuration change or new model attempt was made; budget stays 6/8.

On 2026-10-10 the saved Windows sandbox selection was read as `unelevated`
(only non-secret mode fields were inspected). Following the official
[Windows sandbox guidance](https://learn.chatgpt.com/docs/windows/windows-sandbox),
three bounded native `codex sandbox` probes used the explicit `:workspace`
permission profile and managed configuration in temporary directories:

| Probe | Result |
| --- | --- |
| Absolute current virtual-environment Python; print a synthetic marker | Exit 0, marker present |
| PATH-resolved `python`; print a synthetic marker | Exit 0, marker present |
| Resolved PowerShell, no profile/noninteractive; invoke absolute Python | Exit 0, marker present |

Each subprocess used subscription-safe environment and a 25-second timeout.
No model invocation, API billing, saved configuration change, elevated setup,
new Windows account, firewall change or installation replacement occurred.
Temporary probe directories were managed by the diagnostic helper and contain
no user work. No sandbox-secrets directory was opened.

The previously reported permission failure is **not reproduced** by these
current startup probes. They do not reproduce the old model-generated command,
its exact permissions metadata, runtime cwd, Python arguments or shell profile.
Do not claim the old sandbox error is repaired or that user/model reporting was
false. The original raw errors are absent; exact historical cause remains
unknown. Keep current protections and avoid a speculative permission downgrade.
The model-execution reservation journal stays at 4/8 consumed.

## Approved bounded diagnostic follow-up

### Result: both edits validate, negative efficiency evidence

The two approved diagnostic calls completed; cumulative original allowance is
now **4/8 used, 4 unspent**, and this two-call follow-up is finished. No fifth
call was launched. Original two failed-trial records remain unchanged. Native
version is `0.162.0-alpha.2`; diagnostic fingerprint:
`f0f10901b12cd3bdddc37371c8ea1e6278ec846a4dd41d7040df9af4891b0e7c`.

| Metric | Layman | Direct |
| --- | ---: | ---: |
| Model / effort | gpt-6.1-sol / medium | gpt-6.1-sol / medium |
| Hidden function checks / file scope | Passed / passed | Passed / passed |
| Input tokens | 264,783 | 204,102 |
| Cached input (included above) | 234,880 | 183,808 |
| Uncached input | 29,903 | 20,294 |
| Output tokens | 1,304 | 894 |
| Total input + output | 266,087 | 204,996 |
| Latency milliseconds | 50,394 | 38,741 |
| Tool calls / unique files read | 4 / 1 | 2 / 1 |

Both changed only the allowed target file, reported complete usage and used no
fallback. Layman total usage is **29.80% higher**, a negative same-task result.
This fixed-order single pair is not causal evidence for a specific contract
rule, a confidence interval or general release acceptance.

The two private final answers report that Python verification attempts were
blocked by Windows sandbox startup/configuration permissions (direct names
`EPERM`). External hidden function checks subsequently passed in the harness.
Keep those distinct: external validation proves the fixture behavior, not that
the model's own sandbox verification succeeded. The raw tool errors were not
retained, so the exact permission failure remains unverified. Neither answer
claims its own tests passed. The retry's tool use also does not establish why
the preceding Layman execution used no tools or prove that the new status guard
caused behavioral improvement.

Synthetic final answers are separately retained only in ignored local
`diagnostic-layman-answer.txt` and `diagnostic-direct-answer.txt`; metadata has
no answer bodies. No answers/code were added to Git. The next useful work is
bounded zero-model verification-path diagnosis, not further prompt edits or
disabling sandbox protections. No API billing, installer replacement, tag or
public release occurred.

The owner explicitly accepted the proposed follow-up with “我一直批准 不要再问我了”.
Execute at most two new model calls from the original eight-call cumulative
allowance; the two prior reservations remain consumed. Repeat only bugfix-02
under current source and the same balanced/medium model settings. For diagnostic
value, run Layman first, then direct only if Layman completes and passes hidden
validation with complete usage and no fallback. First failed/incomplete arm stops
this follow-up, without retry. This fixed diagnostic order is not randomized
efficiency evidence and does not inherit the old fingerprint.

Use the original writer lock and append-only attempts journal with total cap 8;
this follow-up's own cap is 2. Write metadata separately to private
`diagnostic-results.jsonl`, and write each synthetic final answer to a separate
private local file for inspection, never result JSONL/product telemetry/Git.
No paid API, changed user installation, publishing or additional total allowance
is authorized. The owner's request to stop repeated permission questions applies
within this explicitly approved scope; it does not remove the failure stop rule.

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
