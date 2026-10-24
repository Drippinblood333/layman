# Current-default calibration stopped by configuration drift

## Outcome

The Direct arm completed and passed the fixed hidden function and file-scope
checks, but the post-execution configuration fingerprint differed from preflight.
The production benchmark guard immediately marked comparison status
`needs_verification`, retained native status `completed` and incurred usage, and
created the durable closed-trial marker. **No Layman arm ran; no paired token
comparison or savings percentage is valid.**

One reservation and one result exist. The unused second slot is closed, not
available to retry under another path or cap. A zero-model replay check confirmed
the closed journal refuses entry before native resolution. Do not start another
paired experiment merely to work around this stop: first explain/control the
configuration drift, using non-model diagnostics where possible.

| Direct observation | Value |
| --- | ---: |
| Input tokens, including cached subset | 75,210 |
| Cached input subset | 62,720 |
| Output tokens, including reasoning subset | 559 |
| Reasoning subset | 33 |
| Total input + output | 75,769 |
| Tool calls | 4 |
| Compactions | 0 |
| Runner latency | 30,984 ms |

Only `src/target.py` changed in the synthetic fixture. Complete usage and passing
automated checks do not override the failed configuration comparability gate.
Zero observed compactions also means this cannot validate compaction quality or
the causal effect of preserving the native compaction prompt.

## Preregistered scope

Following the owner's continuing execution/evaluation authorization, the assistant
set a new cumulative ceiling of **two whole subscription task executions**,
including failure/interruption, before any launch. No paid API, reset credit,
installed-runtime replacement, release tag or publication. Old trials and their
closed/exhausted allowances were not reopened or migrated.

- Source HEAD `5b07075` (documentation-only follow-up to verified product source
  `8b1aa177f77003fca88417944aea90221ece2c22`). No implementation changed mid-run.
- Preselected public `bugfix-06` task, private ID
  `bugfix-06-postcompact-calibration`, not a fresh holdout or real-user sample.
  Hidden checks were extended before execution for each forbidden character,
  empty/whitespace inputs, outer trimming, internal spaces and Unicode retention.
- Same task/reminder, initial bytes, allowed-file list and frozen hidden checks
  intended for both arms; Sol/medium required by preflight. Seed `2026102406`
  selected Direct then Layman before calls. No outcome-based order selection.
- Existing arm-specific budgets were retained: intended default end-to-end
  observation, not a same-budget or compaction-only causal experiment.
- Four private official alpha.20 executable component hashes matched the previously
  verified runtime set; the user's existing installation was not replaced.
- Official `account/rateLimits/read` preflight found 73% five-hour and 11% weekly
  usage consumed. No reset was redeemed. Account replies/credentials were not
  retained; only numeric quota-window fields were recorded.
- Offline original FAIL / reference PASS was required. Initial preflight exposed
  an escaping bug in the added hidden-check harness; it was fixed before freeze,
  reservation or model launch. Only the owned temporary fixture was cleaned.
- Driver, protocol, task/validator, execution policy, source and path-aware
  configuration provenance were frozen before the first reservation. Driver and
  protocol hashes were independently checked unchanged after the stop.

Private counters/hashes/protocol are retained under ignored
`build/postcompact-pair-2026-10-24/`. Answer text and model-generated code were not
retained in the journal; the isolated execution fixture was removed by the
existing guarded cleanup. The reference implementation is predeclared fixture
material, not a retained model answer.

## New configuration evidence and next step

Follow-up verified that the config path identity matches preflight and the config
file exists before and after, while its content hash differs. This narrows the
earlier uncertainty about profile/path identity. It does **not** identify the
writer, changed keys or exact cause; the full configuration was not retained,
and a fingerprint snapshot is not a lock. No user configuration was restored,
rewritten, or replaced to force comparability.

The [official eval guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
was searched/fetched before preflight: use task-specific checks and distinguish
metrics from human judgment. The [official app-server documentation](https://learn.chatgpt.com/docs/app-server)
documents the read-only rate-limit RPC used here. No Evals platform or model judge
was invoked. Continue with a zero-model before/after key-level diagnostic that
keeps values in memory only; do not spend another task execution to diagnose this.

## Zero-model key-level follow-up

The next bounded diagnostic used the same verified private runtime and actual
current config path. Parsed configuration values stayed in memory; only hashes,
changed top-level key labels and process/request counters were eligible for its
private report. Unknown key labels are hashed rather than printing dynamic paths.
The probe itself never writes the user's configuration. Existing auth was not
copied into another profile. No write/config-update RPC was sent.

| Stage | Observed outcome | Observed config delta |
| --- | --- | --- |
| Passive, no native process | 5 seconds | None |
| Native version query | Exit 0 | None |
| Native effective config-read presence check | Completed; developer instructions absent | None |
| Native workspace-write startup with local refusing provider | Exit 1 before the 12-second deadline | None |

The synthetic provider uses a non-reserved ID, binds only 127.0.0.1, refuses all
requests with HTTP 400 and never forwards them. Three local HTTP requests had
326,424 body bytes discarded without retention; no real model response/generation
occurred. This is not a complete external-network/auth-store audit. A later
inventory found zero visible processes under the private runtime directory, and
the user's config hash still matched the probe's end snapshot. Only synthetic
workspace/report files were created in ignored `build/config-drift-keys-2026-10-24/`.

No raw or parsed config changes were observed before/after stages or by a 100 ms
watcher during them; changed-key lists are empty. Polling can miss transient
changes, and this does not rule out another writer. It does not identify which
keys changed during the earlier real execution, restore comparability, or reopen
the trial. The older isolated workspace-write timeout is a different condition
and is not relabeled as passed by this probe.

The [official app-server API](https://learn.chatgpt.com/docs/app-server)
distinguishes effective `config/read` from `config/value/write` and
`config/batchWrite`; documentation was searched/fetched before this follow-up.
These observations narrow the tested conditions only: passive observation,
version/config read and refused startup did not reproduce the drift. The next
diagnostic should use a local synthetic successful completion, not a real model,
to separate successful native completion from failed startup. The old closed
journal still has one reservation; no product source, CI or model trial restarted.

## Synthetic successful-completion and command follow-up

The next batch exercised successful native completion without real inference.
A loopback-only fixture sent fixed Responses SSE lifecycle/message events after
discarding incoming bodies. It never forwarded a request or used a model backend.
Only synthetic text was returned; reported fixture usage zeros are NOT measured
model token usage and cannot support savings, cost or billing claims.
The [official Responses streaming guide](https://developers.openai.com/api/docs/guides/streaming-responses)
was searched/fetched before constructing these events.

| Condition | Observed native outcome | Observed config delta |
| --- | --- | --- |
| Fixed assistant completion, no command | Exit 0, fixed last-message matched | None |
| Initial command probe with mistaken zero tool budget | Exit 1, budget_exceeded; roundtrip incomplete | None; not a pass |
| Corrected command probe, tool/file ceiling 2 | Exit 0, one tool call, no command failures, tool output returned, fixed last-message matched | None |
| Same command with Direct's explicit workspace permission profile and medium effort | Exit 0, one tool call, no command failures, tool output returned, fixed last-message matched | None |

The one commanded action was `Get-Location`, run in the owned synthetic workspace.
The corrected/profiling probes each sent one synthetic function call, observed its
matching output in the next request and sent a final synthetic message. They did
not edit project code. The last variant aligned `default_permissions=":workspace"`,
`CODEX_PERMISSION_PROFILE=:workspace` and medium effort with the real Direct
launcher after source inspection exposed the missing comparison condition.
The provider remained the non-reserved local diagnostic provider, not the official
authenticated inference path; this remains an important difference.

Each condition has its own guarded result directory under ignored `build/`:
`config-success-keys-2026-10-24`, `config-tool-keys-2026-10-24`,
`config-tool-keys-2026-10-24-permitted` and `config-tool-profile-2026-10-24`.
The mistaken zero-budget result is retained unchanged. Corrected variants record
their in-memory source hashes and reuse the earlier snapshot/monitor definitions
without rerunning or overwriting that earlier probe's actions/results.

No raw/parsed configuration delta or sampled transition was observed in these
conditions. The final config hash still matches the probe end, and later visible
process inventory found zero private-runtime processes. The sealed real-model
journal still contains exactly one reservation; no real model generation,
benchmark restart, production code change, config write by the probe or CI run.

This narrows the conditions tested, not the root cause: local successful completion
and this one read-only command did not reproduce the earlier real-call drift.
It does not rule out authenticated-provider behavior, file-changing tasks,
different command paths or concurrent writers, and 100 ms sampling can miss
transient changes. Stop adding low-value probe variants here. Do not launch a
fresh model pair as a diagnostic retry; a subsequent investigation needs a concrete
new hypothesis or passive change evidence from ordinary authorized activity.

## Full-goal boundary

Current evidence still does not close the owner's objective:

- Installation/size: candidate Windows binaries exist and were measured near
  16.5 MiB, with source/install smoke evidence, but a fresh GitHub release listing
  returned no public releases. The documented standalone latest-release path
  therefore still has no public installable target.
- Ease of use/prompt clarification: bounded offline checks, brief planning and
  matching English/Chinese questions are implemented; these are not general
  semantic prompt optimization or real-user usability acceptance.
- Lean execution/input/output: concrete redundant classification/import/traversal
  work was removed and intent-preserving controls tested. Their local CPU/byte
  results are not task-token measurements.
- Same-quality token benefit: the earlier three valid calibration pairs used
  26.86% more total tokens for Layman, and this new trial has no pair. Limited
  positive synthetic log-component results do not establish a default-workflow
  benefit. The overall goal remains active, not completed or blocked.
