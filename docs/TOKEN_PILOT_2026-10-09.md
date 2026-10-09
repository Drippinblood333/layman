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
