# Approved eight-execution development trial

## Predeclared protocol

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
