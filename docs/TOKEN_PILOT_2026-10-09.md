# Subscription token pilot: stopped, no savings claim

The owner approved at most 12 whole Codex task executions through ChatGPT login, without an API key. The six-category calibration pilot used seed `20261009`, code commit `a1ea2033ab7c2491d2b178a25e4fc4d515281f5e`, and experiment digest `089ae145009b7920d6a387b498516c004b7ba85d7be811133517642ba013e330`.

Two attempts were reserved and recorded before the pilot stopped on an execution failure. Ten remain under the original cap; no further model execution was launched after the failure. Local records and the persistent reservation journal are under `build/token-pilot-2026-10-09/`. Do not delete the journal, increase the cap, or change the output path to bypass approval.

| Task / arm | Execution | Hidden validation | Input | Cached input (subset of input) | Output | Total | Time |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| bugfix-01 / Layman | completed | passed | 274,934 | 245,504 | 2,180 | 277,114 | 244,562 ms |
| bugfix-01 / direct | failed (`codex_exit_1`) | failed | unavailable | unavailable | unavailable | unavailable | 54 ms |

Both arms selected GPT-6.1 Sol / medium. Layman recorded five tool calls, one unique file read and zero compactions. Only `src/target.py` changed. Cached input is already included in total input; it must not be added again or equated with subscription charges. The failed direct record contains zero counts with `usage_incomplete=true`, not evidence of free execution.

There are zero usage-eligible pairs, so no token reduction can be calculated. The Layman task passed automated hidden checks, not human semantic review. Its large input count warrants investigation, but the retained metadata alone cannot establish the cause. The original direct failure retained only a generic error category; neither its precise cause nor whether it reached a provider can be established retrospectively. No raw prompt, answer, generated code or error text is published or retained in telemetry.

The follow-up adds privacy-preserving classification of structured CLI error events and known configuration/argument diagnostics. Synthetic tests pass without model calls. This improves future diagnosis; it does not retroactively explain this failure. A changed source fingerprint must not pool results with this experiment. All historical reservations still count against the original cap.

Next: diagnose the direct startup failure with non-model checks, then decide whether a bounded continuation is useful. Do not spend the remaining attempts on speculative retries. Six calibration pairs cannot close the 30-pair public savings gate; this subscription path also does not exercise the API-only lossless tool-output encoder. No installed executable was replaced, no API-key call was made, and no release tag or public release was created.

## Zero-call diagnosis and measurement repair

Offline checks confirmed that the direct command's argument parser and configuration/prompt rendering succeed. They did not execute a task and cannot establish the original startup-failure cause. A clean synthetic fixture's 115-character task loaded 17,037 characters of message text, including 12,923 characters of skill-bearing developer context, through the existing user configuration. Fourteen plugins were enabled. These are character counts, not token counts, and do not establish which context caused the recorded high input usage.

A synthetic regression reproduced a measurement defect in both old collectors: a tool result containing `input_tokens=999999` and `output_tokens=8888` overrode the CLI's completed-turn usage of 100 input and 10 output tokens. The original pilot's event stream was deliberately not retained, so the table above remains **old-parser reported counts, not independently verified provider usage**. It cannot be repaired retrospectively or assumed contaminated. Do not use it to establish actual efficiency or savings.

Both execution paths now share a parser that accepts only top-level `turn.completed.usage`, requires valid nonnegative integer input/output fields, rejects booleans and invalid cached counts, recognizes `reasoning_output_tokens`, and sums completed turns without adding cached input twice. Tool payloads cannot create usage availability. Fingerprints now distinguish the measurement protocol; the task benchmark schema is 4 and old-protocol records cannot pass the public savings gate. The source benchmark and adaptive harness also fingerprint the shared measurement implementation. Historical records and the original two reservations remain intact.

The previous published commit `46c2f03` passed three-platform tests and four standalone builds in [CI run 37898897478](https://github.com/Drippinblood333/layman/actions/runs/37898897478). Linux ARM failed at `actions/setup-python` and release assembly was skipped. Subsequent attempts to retrieve detailed failure logs encountered GitHub API EOF errors; the precise infrastructure cause is not established. No workflow retry or release was dispatched during diagnosis.

## Follow-up: delivery and startup observability

Per-command network checks found the inherited local proxy path failing TLS/EOF while direct GitHub access succeeded. No system, proxy, Git or account configuration was changed. Commit `6b619aad65d889c8e6124d8445c0f11af6ccd64d` was pushed using a single-command proxy override, and its exact identity was verified on remote `main`. [CI run 37914547716](https://github.com/Drippinblood333/layman/actions/runs/37914547716) was observed in progress; this is not a passing result.

The earlier Linux ARM failure logs are now accessible: the Python archive downloaded and extracted, but setup's pip initialization repeatedly encountered `[Errno -3] Temporary failure in name resolution`, then failed to find pip. This establishes a runner DNS failure during setup, not a failing Layman test or proof that pip was unavailable upstream. No blind workflow/dependency change or retry was dispatched.

Future direct-arm records now include native exit code, whether stderr was present, and counts of the five known top-level lifecycle event types. Nested tool events and unknown payloads cannot populate these counters; raw diagnostic text, thread IDs and answer text remain excluded. Two offline regressions cover privacy and startup failure with missing usage. These fields cannot retroactively identify the original direct failure or prove whether a provider request occurred. The original reservation journal still contains exactly two attempts, and no model execution was launched in this follow-up.

## One-attempt direct diagnostic after hosted verification

Commit `f7821ea949a0838179ecc1af0b251320df4019d8` passed all ten validation jobs in [CI run 37914821030](https://github.com/Drippinblood333/layman/actions/runs/37914821030), including three-platform tests, five standalone installation builds, Docker and release assembly. The publish job was skipped; no release occurred. This checkpoint has 259 router tests plus 41 adaptive tests (300 total).

After that verification, one direct-only diagnostic used the existing approved output/journal and total cap of 12, seed `20261010`, `--max-calls 1`, and fingerprint `4b825f2d2a59a5f19eecab8c0d760c1b9b3218ae9090c1d5a3510e12a0b9ab60`. The order was fixed before execution to start with `bugfix-01:direct`; this is startup diagnosis, not a newly randomized savings trial. The arm failed in 57 ms with native exit 1, stderr present, and zero top-level thread/turn/error lifecycle events. No source files changed, hidden validation failed, and usage is incomplete. The failure is localized to before any observed session events; the precise cause and whether a provider request occurred remain unproven. No automatic retry or second arm was launched.

The journal now has **three reserved executions and nine remaining authorized attempts**, counting the failed diagnostic. The runner's `remaining` field counts unfinished experiment arms (11 here), not authorized executions. A separate `authorized_attempts_remaining` field now makes that distinction explicit, with restart-cap regression coverage. The old pilot is not pooled with this diagnostic, and there are still zero usable new token-comparison pairs. The next action is a no-model examination of startup/configuration differences, not another blind retry.

## Zero-call launch parity follow-up

Source inspection found a launch difference: the streamed Layman runner creates a new Windows process group (or a new session on POSIX), while the direct baseline used the default child-process launch. A shared `process_launch_options` helper now preserves the existing streamed behavior and applies it to direct execution too. Platform regressions cover both branches, and the baseline test checks the actual subprocess arguments. This removes a confirmed infrastructure difference; it **does not establish the cause of the 57 ms failure or prove the baseline now works**. No task execution was launched for this follow-up, and the original budget remains 3/12 used, 9 remaining.

The local cached catalog lists `medium` among GPT-6.1 Sol's supported reasoning levels, so an unsupported effort is not supported by that local evidence. The catalog may differ from current account/server availability and is not a live access test. Argument parsing and offline prompt rendering already pass; runtime startup is still unverified.

Local verification for the parity change passes 261 router plus 41 adaptive tests (302 total), configured lint and secret scanning. The exact-head hosted checkpoint remains `f7821ea`, not these subsequent local changes. GitHub direct access subsequently failed again, including a read-only remote check, so no remote delivery or CI result for this parity candidate is claimed. No global network configuration was changed and no speculative dependency downgrade, install replacement, tag or release occurred.
