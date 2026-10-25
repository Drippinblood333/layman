# Configuration isolation: bounded feasibility evidence

## Question and official mechanism

The October 24 real-model pair remains sealed after user-configuration drift.
Prior local startup/completion/tool controls did not identify the writer. Instead
of another real-model retry or another variant of those controls, this batch
checked a distinct mechanism: can native execution omit the mutable base user
configuration without copying credentials into a different home?

The searched and fetched [official exec reference](https://learn.chatgpt.com/docs/developer-commands#codex-exec)
documents `--ignore-user-config`: do not load `$CODEX_HOME/config.toml`, while
authentication still uses `CODEX_HOME`. Profiles are overlays on the base config,
not a documented immutable replacement. The private, previously hash-verified
Codex `0.162.0-alpha.20` binary's `exec --help` lists the ignore flag as well.

## Zero-model differential check

The retained private probe is `build/config-isolation-2026-10-25/probe.py`, with
its own `result.json`. All four runtime component hashes match the previous
frozen runtime. Probe SHA-256:
`68579a6cc886d382e730f91911e59d7daf645e45a88c1158c7a0c270e3e7adf8`.

Both starts use the same owned synthetic workspace/home, a deliberately invalid
synthetic `config.toml`, read-only sandbox, zero permitted tool/file calls and
12-second deadline. The only command difference is the ignore flag. A custom
no-auth provider points to a loopback server that always returns HTTP 400, never
forwards a request, discards bodies and produces no model response. No credential
file was copied or linked. API-key variables are stripped by the existing
subscription environment helper; the native process receives the synthetic home.

| Native condition | Result | Local requests | Synthetic config |
| --- | --- | --- | --- |
| Ordinary config loading | Exit 1, config error observed | 0 | Unchanged |
| `--ignore-user-config` | Exit 1, no config error observed; local rejection reached | 1, 41,123 body bytes discarded | Unchanged |

Neither start timed out or reported usable token usage. Both exit codes are
expected failures, **not successful model tasks**. The second start shows the
malformed base config was bypassed, not authenticated execution or a complete
configuration freeze. No private-runtime process remained in the subsequent
visible process inventory. The historical real trial still has one reservation,
one result and its closed marker; it was not reopened or reused.

## Decision and limits

Keep the production default and existing raw-byte drift guard unchanged. Do not
silently add this flag to ordinary Layman execution: it would omit user settings,
including potentially relevant developer instructions, tool/plugin setup and
compaction choices, contrary to intent-preservation requirements.

This establishes a candidate mechanism for a separately declared controlled
experiment, not the missing default-workflow comparison. Any such experiment
must give both arms the same explicitly frozen settings, verify instruction and
permission parity, label the excluded configuration, and keep a separate protocol,
journal and newly bounded execution allowance. Its result could not be relabeled
as current-default benefit. No such experiment was implemented or launched here.
The documentation's authentication behavior was not exercised with real credentials;
no claim of complete network/auth-store auditing is made.

The original config writer remains unknown. This investigation changes the
available experiment-design options, not that diagnosis or the full objective.
No paid API, real-model generation, installation replacement, tag or release.

