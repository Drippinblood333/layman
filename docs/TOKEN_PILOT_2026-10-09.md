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

## Delivery and clean-install credential isolation

Connectivity recovered, and remote `main` was verified at `8981319cb65dae8bd36e69d45c2c7c7895a282e1`. [CI run 37916201617](https://github.com/Drippinblood333/layman/actions/runs/37916201617) passed all ten validation jobs including release assembly; publication was skipped. This supersedes the earlier pending-delivery status, but not the unresolved startup diagnosis or efficiency gates.

Local wheel and source builds and their temporary-environment installation checks passed. The initial smoke inherited an unnecessary `OPENAI_API_KEY` environment setting (only its presence, never its value, was reported). The check did not start a service or perform a model call. The smoke runner now strips known model/account credentials, router overrides and Python import overrides, bootstraps pip with the sanitized child environment, and runs installation/inspection/CLI checks from the temporary directory instead of the repository. Parent environment and installed user application are unchanged. This is environment isolation, not an operating-system sandbox or a guarantee that dependencies cannot access other files.

Both artifacts passed again after hardening, with `openai_api_key=missing`, `admin_token=missing`, service offline, loopback-only configuration and a writable temporary database directory. Nineteen bundled plugin files matched source hashes in each installation. Two regressions verify credential/config/import environment removal, preservation of the parent dictionary, and explicit temporary subprocess working directories. Full local suites pass 263 router plus 41 adaptive tests (304 total), lint and secret scanning. This smoke-script hardening still needs its own hosted check.

The tested artifact SHA-256 values for code `8981319` are:

- `layman_codex-1.0.0-py3-none-any.whl`: `be9992ecaa3fa6000a5748f37e946e28462a95868264842653139c02236fddc5`
- `layman_codex-1.0.0.tar.gz`: `206baf41a1433e767034b6efdbf4b52494b8074b99a0b7578c7c680376b1d0d2`

Artifacts remain under ignored `build/launch-parity-python-packages`; no release or installation replacement occurred. The authorized task budget remains 3/12 used and 9 remaining. No runtime task was retried in this follow-up, and no token-saving claim is supported.

## Fourth reserved attempt and relative-path defect

Commit `80c1a4d67c67872bf514ac5b01753c342e02bb14` passed all ten jobs in [CI run 37917059279](https://github.com/Drippinblood333/layman/actions/runs/37917059279), including hardened clean-install smoke and release assembly; publication was skipped. After that verification, exactly one direct diagnostic was reserved under the original cap, with seed `20261010`, maximum one execution and fingerprint `58a1de9c8f14413d1a77c4bc75bbd3425943a37736b8b723ec51b300af12a1bc`. It failed after 55 ms, exit 1, stderr present, zero observed lifecycle events and incomplete usage. A transient wrapper reported only fixed keyword-presence booleans; all were false and no raw error text was retained. Process-group parity therefore did not resolve the failure in this setup. No second arm or retry was launched. The original journal now has **4/12 attempts used, 8 remaining**.

Source inspection identified an independent concrete defect in the direct arm: when `--work-root` is relative, it supplies a relative task directory both as subprocess `cwd` and CLI `-C`. Codex then resolves `-C` again from within that task directory. Layman already resolves its directory to an absolute path.

Two zero-model prompt-render probes from a clean synthetic fixture verified the actual rendered directory, not merely a hypothesized path:

| CLI directory argument | Renderer exit | Rendered directory equals fixture | Rendered directory exists |
| --- | ---: | --- | --- |
| original relative path | 0 | no | no |
| resolved absolute path | 0 | yes | yes |

The debug renderer itself does not reject the nonexistent directory. This reproduces incorrect path resolution, but is not a successful runtime task or retrospective proof that no other startup error occurred. The direct arm now resolves the workspace before setting both subprocess `cwd` and CLI `-C`. A regression exercises a relative work root and checks both absolute launch arguments and usage availability with a fake process, without model calls. Local suites pass 264 router plus 41 adaptive tests (305 total), lint and secret scanning. The path repair still needs hosted verification and a separately budgeted runtime retest. No fifth attempt was made in this batch, and no token-saving claim is supported.

## Fifth attempt: corrected direct workspace passes runtime validation

Remote GitHub verification was still failing, but the path repair had 305 passing local tests and a native zero-model path-render check. One local diagnostic under code `a9dc9ecca0fcac243c8ac234fdea1a4c7859a107` used the original output/journal, seed `20261010`, maximum one launch and unchanged total cap 12. This local runtime check does not replace the pending hosted verification or authorize publication.

The corrected `bugfix-01:direct` completed and passed hidden function/scope validation, changing only `src/target.py`. It reported exactly one thread start, one turn start and one completed turn, with no failed-turn/error events. Usage is complete under the trusted completed-turn parser:

| Model / effort | Input | Cached input (included in input) | Output | Reasoning (included in output) | Total | Time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GPT-6.1 Sol / medium | 279,649 | 256,768 | 1,673 | 136 | 281,322 | 120,449 ms |

Fingerprint: `4e2f7655bed3d194ecaf9cadf7fbb01df49e077bf0451045b64e45acbfc138c5`. One unique file read and zero compactions were reported. The direct collector reported 10 tool item events; unlike the streamed collector, its legacy metric may count started/completed events twice, so this number is not an audited unique-tool-call comparison. It is not a public savings gate. Usage and validation are separate from that tool metric.

This establishes that the directory-corrected direct arm can execute this task in the current setup. It does not establish success for all tasks, human semantic review or token savings. The substantial input count is now backed by a completed-turn usage event; its precise context-source breakdown has not been measured. Cached input must not be added twice or converted into a subscription invoice.

The original journal now contains **5/12 reserved executions, 7 remaining**. No second execution was launched in this batch. No raw prompt, answer, generated code or stderr was retained. There is one usable direct baseline but no same-fingerprint Layman result yet; older experiments must not be pooled with it. The next useful runtime check is the matching Layman arm under this same code/protocol, after confirming safe delivery. No API-key billing, local installation replacement, tag or public release occurred.

## Sixth attempt: first usable pair is a negative efficiency result

Before launch, the current source/CLI fingerprint was verified equal to the successful direct baseline, the next pending arm was `bugfix-01:layman`, ChatGPT login passed and the journal contained five reservations. One matching Layman execution was launched under the unchanged total cap. No source files or execution policy changed during either arm. It completed and passed the same hidden function/scope validation, changing only `src/target.py`.

| Arm | Input | Cached input (subset) | Output | Reasoning (subset of output) | Total | Time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Direct | 279,649 | 256,768 | 1,673 | 136 | 281,322 | 120,449 ms |
| Layman | 299,021 | 281,088 | 1,962 | 233 | 300,983 | 129,529 ms |

Both used GPT-6.1 Sol / medium, reported complete completed-turn usage, read one unique file and recorded zero compactions. The Layman tracker reported five unique tool operations; the direct legacy collector's ten item events are not a comparable unique-tool count. No raw transcripts or generated files were retained, and no human semantic review occurred.

Fingerprint remains `4e2f7655bed3d194ecaf9cadf7fbb01df49e077bf0451045b64e45acbfc138c5`. Analysis has exactly one usage-eligible pair: Layman used **6.99% more total tokens** and **17.27% more output tokens** on this task. Both passed automated validation. The public savings gate is false. A bootstrap over a single pair has no meaningful generalization value, even though the current analyzer prints a degenerate interval. Cached/uncached differences are not a subscription invoice or an independent randomized cache study.

The original journal now contains **6/12 reserved executions, 6 remaining**. No additional arm was launched after this negative result. Preserve it when designing context/prompt changes; do not pool older fingerprints, discard the direct failure history, or advertise general savings. The next useful step is zero-model context-overhead analysis before spending more attempts. GitHub read access briefly worked, but a subsequent push and verification failed; remote delivery remains unconfirmed for the path-corrected source and this report. No configuration replacement, API-key evaluation, release tag or public release occurred.

## Zero-model follow-up: contract overhead and metric parity

Native `debug prompt-input` rendered the actual captured direct/Layman launch settings for the same synthetic fixture, without a model request. Launch capture used a fake runner; its fake login/usage is not authentication or experimental evidence. Only numeric message metadata was displayed, with no raw context saved. Shared message text was 18,082 characters. Before the candidate change, Layman added exactly 842 contract characters (18,924 total); after shortening it, Layman adds 583 (18,665 total), a 259-character reduction. The large shared skill context is retained. Counts exclude tool schemas and provider-internal context and are not token counts; they do not explain the full observed usage difference or establish task savings.

The shorter contract preserves request/scope, conditional implementation authorization, read-only protection, symbol/test-first reads, file/tool ceilings, evidence-gap-only expansion, evidence reuse and verification/risk reporting. Final-answer length is explicitly a soft upper guide, never a padding target or reason to truncate necessary detail. Model, effort, hard execution controller and permissions are unchanged. Six regression combinations cover every tier and both permission modes.

The direct/buffered `event_metrics` collector now uses the same `EventBudgetTracker` as streamed execution. A regression confirms that started/completed events sharing one operation ID produce one call and one file, not two calls. This fixes reporting parity, not actual runtime work. Historical records cannot be retroactively corrected because raw events were intentionally not retained. The preserved pair's token values and negative result are unchanged; the old direct count remains explicitly non-comparable.

All 312 local tests (271 router plus 41 adaptive), configured lint, secret scanning and whitespace validation pass. No additional execution reservation or model request occurred; **6/12 used, 6 remaining** in the original journal. Contract/collector source changes require a new experiment fingerprint, so subsequent measurements must not be pooled with the prior pair. Hosted verification remains pending. No API billing, installed configuration replacement, tag or public release occurred.

## Delivery and installation verification of the shorter-contract candidate

Remote `main` was read back at exact source commit `b23b067e21d984f59cb993124f645387f6c6674d` after the authorized push. [CI run 37929656288](https://github.com/Drippinblood333/layman/actions/runs/37929656288) reached terminal success: three OS test jobs, five standalone build/lifecycle jobs, Docker and release-asset assembly all passed. Publication was skipped. The earlier direct-path repair and preserved negative report are now delivered as ancestors of this commit. No CI retry was dispatched.

A fresh local wheel/source build from this source passed the credential-isolated clean-install smoke, verifying 19 bundled files, CLI help and doctor for each package. Both reported missing API/admin credentials, loopback listen configuration, writable temporary database parent and offline service. The user's installed program/configuration was not replaced.

| Local candidate artifact under `build/contract-parity-python-packages` | SHA-256 |
| --- | --- |
| `layman_codex-1.0.0-py3-none-any.whl` | `1524bc4464b254abca144a63ecb36307e05aa96b2baabfffb57590f05c8937cb` |
| `layman_codex-1.0.0.tar.gz` | `17173ca1cf0fafb1d37a88969cfb1a6e22d80b77fd527f387141d734bb6f4d61` |

The no-execution pilot planner confirms that this source has no completed arms under its new source digest, and the next planned arm is `bugfix-01:direct`. The original authorization journal still has six reservations; new fingerprints do not reset the remaining six-attempt cap. These packaging/CI results are not whole-task efficiency evidence. A new matched pair remains the next runtime calibration step; fresh holdout quality, human acceptance and owner-authorized prerelease/publication remain open.
