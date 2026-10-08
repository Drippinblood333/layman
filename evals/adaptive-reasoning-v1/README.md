# Adaptive Reasoning v1

This benchmark measures the lowest sufficient explicit `model × reasoning effort` arm for 30 new, human-reviewable holdout tasks. Existing FAST/BALANCED/DEEP labels are never used as ground truth; the current Layman route is computed only as a post-experiment comparison.

## Safety and scope

- Default mode is dry-run. No model call occurs without the `execute` command, `--approve-model-calls`, a positive `--max-calls`, and a positive `--max-estimated-usd`.
- Every arm receives the same case prompt, common instructions, fixture, tools, history, output cap, validator, cache declaration, and execution policy. Only model and reasoning effort vary.
- Each attempt starts from a new fixture copy. High-risk cases are read-only and reject workspace mutations.
- Results are append-only and flushed with `fsync` after every reservation and result.
- Prompt, answer, code, tool arguments, and event transcripts are not written to results. Answer storage requires `--store-outputs`.
- This framework does not modify or call the production Router. It computes the current Router arm offline for comparison only.

## Commands

```powershell
# Corpus, fixture, validator and protocol validation; no model calls.
python evals/adaptive-reasoning-v1/benchmark.py validate-only

# Randomized plan, fingerprint, resume state and budget ceiling; no model calls.
python evals/adaptive-reasoning-v1/benchmark.py dry-run --max-calls 180 --max-estimated-usd 200

# Explicitly gated execution. Do not run until spend/model calls are approved.
python evals/adaptive-reasoning-v1/benchmark.py execute --approve-model-calls --max-calls 6 --max-estimated-usd 10

# Analyze durable results plus optional blind/manual semantic reviews.
python evals/adaptive-reasoning-v1/benchmark.py analyze

# After explicitly storing outputs, create an arm-blind rubric queue.
python evals/adaptive-reasoning-v1/benchmark.py review-plan

# Explicitly gated blind-judge execution; no call occurs without approval and budgets.
python evals/adaptive-reasoning-v1/benchmark.py judge --approve-model-calls --max-calls 6 --max-estimated-usd 2
```

The six core execution arms produce 180 task calls. The 13 cases requiring semantic review can add up to 78 blind-judge calls if every core-arm output receives one judge score. Human review covers every borderline/disagreement and a deterministic 20% sample; it does not add model calls.

Review submissions use only `case_id` plus an opaque `blind_label`; the reviewer-facing plan does not expose model, effort, route tier, or arm ID. A required human sample is not considered sufficient until a human review record exists.

Semantic arms stop before execution unless `--store-outputs` is explicitly present, because a later blind review cannot be performed after discarding the answer. Deterministic arms never require output storage. The stored filenames use opaque blind labels rather than arm IDs.

## Sufficiency

An arm is sufficient only when execution, deterministic/hidden validation when applicable, safety, and evidence checks pass; semantic quality is at least 4.0/5; and it is within 0.25 of that case's highest otherwise-qualified arm. Deterministic cases derive a 5.0/0.0 quality score from hidden validation. Debugging, architecture and high-risk read-only cases require blind rubric scores and human review flags.

Among sufficient arms, selection minimizes total successful-outcome estimated cost, including failed attempts and retries. Costs within 2% or $0.0001 are treated as close, then lower end-to-end latency wins.

The experiment uses `pricing-snapshot.json`, an experiment-only snapshot of official OpenAI standard short-context prices and supported reasoning efforts. Repeat `--case-id` to run an exact holdout subset, and use `--max-retries 0` for a no-retry acceptance run. Launcher, rate-limit, network, and timeout failures stop the active run instead of being hidden by repeated retries.

## Execution backend preflight

`execution_backend.py` separates launcher resolution, zero-call preflight, execution, and infrastructure-error classification. On Windows, the benchmark directly spawns a verified native PE executable with `shell=False`. Command and PowerShell shims are reported but rejected as experiment launchers; prompt, task, tool, and workspace content is never interpolated into a shell command string.

Run an exact zero-call preflight before execution:

```powershell
python evals/adaptive-reasoning-v1/benchmark.py preflight `
  --case-id mech-inventory-reconcile --arm-id sol-medium --max-retries 0
```

The preflight checks version startup, ChatGPT login, captured stdout/stderr, the observed working directory, bundled model/effort capability, and bounded process cancellation. It then materializes the selected case with the normal fixture builder and validates the exact execution contract by replacing the stdin prompt sentinel with `--help`; this parses the real model, effort, sandbox, JSONL, ephemeral, user-config isolation, Git-check, working-directory, and output-file arguments without starting a model.

On the local Codex CLI 0.160.0 checked on 2026-10-09, the five `luna-low`, `sol-low`, `sol-medium`, `astra-medium`, and `astra-high` arms pass zero-call preflight. The CLI catalog does not expose Luna's `none` effort, although the API supports it. The full six-arm Codex experiment is therefore blocked before model calls. An explicitly selected five-arm subset has a different fingerprint and cannot close the six-arm comparison gate; retain the missing-arm limitation in its analysis.

Prompts are passed only through an explicit stdin pipe and `communicate(input=...)` closes the pipe after writing. They are never placed in the argument array or a shell command. `--skip-git-repo-check` is accepted only when the fixture is a child of the configured benchmark work root, and `--ignore-user-config` isolates experiment variables while retaining the existing `CODEX_HOME` authentication. The stable execution semantics and their digest are included in the experiment fingerprint. A failed preflight starts zero model calls and writes no benchmark sample; direct execution is also blocked until the backend instance has passed this contract preflight.
