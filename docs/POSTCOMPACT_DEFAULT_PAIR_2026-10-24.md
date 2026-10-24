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
