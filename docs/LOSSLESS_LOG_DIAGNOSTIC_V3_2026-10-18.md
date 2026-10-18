# V3 log diagnosis: marker equality fails, not JSON structure

## Decision and scope

The second strict-check failure is now localized: encoded output passed JSON
parsing and schema validation, but its marker field did not equal the fixed
expected value. The other five fields matched. Keep encoding experimental/off by
default; no same-quality saving is accepted and no automatic trimming is added.

This was a new, separately preregistered two-invocation diagnostic ceiling, not
a replay of the closed v2 journal. It deliberately reused v1/v2's exact task,
fixture, expected values and schema to investigate that failure, so it is NOT a
holdout or release-quality confirmation. Old records remain unchanged.

## Measurement

Same Sol/medium, verified full private alpha.20 runtime, instruction, schema,
read-only workspace, native settings and zero tool/file budgets. Only raw versus
existing codec representation differed. Source/helper identity:
0bcb998a1c8e39fdc495fda69cdc0a66349b57dd. Offline native render and genuine saved
subscription login passed before reservations. Five-hour preflight 37% used,
weekly 6%; two reset credits untouched. Built-in provider retries were not changed
or independently counted; two CLI invocations do not imply exactly two HTTP calls.

| Metric | Raw | Encoded |
| --- | ---: | ---: |
| Input tokens | 37,351 | 21,332 |
| Cached input tokens | 37,120 | 21,120 |
| Output tokens, including reasoning | 46 | 181 |
| Reported reasoning tokens | 0 | 132 |
| Total input + output | 37,397 | 21,513 |
| Latency, milliseconds | 17,708 | 22,099 |
| JSON parse / schema | PASS / PASS | PASS / PASS |
| Exact fixed fields | 6 / 6 | 5 / 6 |
| Strict quality gate | PASS | FAIL |

Both completed with usage, zero tools/file references/compactions, return code zero
and unchanged real configuration hash. Cache is reported separately, not subtracted
from total; reasoning is not added twice. Lower total usage with failed quality
is not accepted savings. This is subscription usage, not an API invoice measurement.

Exactly two fsynced reservations and two outcomes were verified, along with
protocol/script/helper hashes and usage arithmetic. Stop after the failed gate;
no replacement, fallback, extra invocation, paid API or credit reset. Temporary
answer files were removed. Private journals are under
build/lossless-log-diagnostic-v3-2026-10-18/.

## What is known, and what is not

- first_error, second_error, expected, actual and exit_status matched.
- marker did not match. No answer values or validator exception text were retained.
- It is therefore NOT known whether the mismatch is line endings, whitespace or
  other content. One possible ambiguity to review is whether "complete checkpoint
  line" includes its terminator; this is a hypothesis, not a recovered answer.
- These are strict six-field extraction checks, not coding, repetition-count,
  human root-cause or production API transport tests. Fixed order, high cache reuse
  and a reused synthetic fixture limit any generalization.

Added a small evaluation-only helper that reports parse/schema booleans and
matches for preregistered public field labels. It keeps the old schema-plus-exact-
equality acceptance rule, never repairs/normalizes answers, and distinguishes an
invalid judge schema from model failure. Ten offline cases passed, including
missing/extra fields, invalid types, wrong values and value-free output checks.
Ruff and evidence/diff checks passed. The helper is outside the runtime package;
no user-facing feature, model route or default policy changed.

Next evidence step is to resolve the task's line-boundary specification and use
independent tasks under a new protocol, not rerun this one until it passes.
[Official native usage documentation](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)
was searched/fetched before execution. No formal release or installation change.

## Subsequent offline contract clarification

Added public evaluation-only line-content fixtures, not a new live pilot:
evals/token_optimization/log_contract.py. The future synthetic task now explicitly
excludes CRLF/LF/CR terminators from marker while preserving every other character,
including leading/trailing spaces and tabs. This is a NEW task specification,
not a reinterpretation of the frozen v1-v3 instruction or a recovered model answer.

Three independent hand-authored cases cover LF, CRLF with Chinese/spaces, and CR
with tabs/no final terminator. A separate reference parser derives their expected
answers from raw text and from exactly restored codec output. The exact validator
still rejects added terminators and trimming. All 16 contract/answer-check tests
passed; no model execution, token measurement, default change or repeat build.
Published fixtures/answers are not holdouts and must not be presented as fresh
generalization evidence. Old marker mismatches remain failures with unknown cause.
