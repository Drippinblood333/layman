# Installed-runtime drift and guarded synchronization

## Actual installation versus verified candidate

The current PATH command resolves to `%LOCALAPPDATA%\Layman\bin\layman.exe`.
The directory contained only the executable, without a BUILD inventory. Its
`--version` invocation failed; version text alone therefore cannot identify it.
The cached plugin launcher is still the portable `layman mcp-server`, not a pinned
full path. No plugin refresh was performed in this batch.

The same ASCII translation request was sent to installed/source **dry runs**
in an owned empty workspace with isolated Layman state and no router-config
environment override. No task generation or Codex login was required.

| Evidence | Installed runtime | Verified candidate |
| --- | --- | --- |
| Executable bytes | 28,489,749 | 17,275,087 |
| SHA-256 | `bc4f670c0a6129a0ab69d4f3bc8b2285fc6401a017c61e417bbaf0d9c61465f5` | `2d696157add1d3c18a49f063325136c19acfa44ee4058dea290664a3d5f0c5c7` |
| Fast model in preview | `gpt-5.6-luna` | `gpt-6-luna` |
| Tool-output token limit | 4,000 | 2,000 |
| Final-output target field | Absent (`null` when selected by audit) | 800 |

These sizes are executable bytes, not RAM, whole installation including notices,
or disk use including retained backups/staging. Budgets are controls, not measured
model usage or savings. The source improvements have **not yet replaced** the old
runtime used by existing MCP processes.

## Candidate verification

Downloaded Windows artifact `12588990938` from exact-source
[CI 40168144565](https://github.com/Drippinblood333/layman/actions/runs/40168144565),
source `c35c5b7a517d8bdcda65da6e744931eda05f137f`. All ten source-validation jobs
passed; [main run 40168378532](https://github.com/Drippinblood333/layman/actions/runs/40168378532)
also subsequently passed all ten jobs with zero failures.

Actual downloaded executable hash matches BUILD.json; runtime, component and
bundle-audit file hashes and source lock digest match. Notices/licenses exist.
The candidate's version command succeeds, dry-run matches current source, and
an invalid MCP `dry_run: null` is rejected before execution. These are isolated
CLI/MCP checks, not a completed owner-installation, restarted desktop-plugin,
authenticated-model or clean-OS acceptance pass.

Private evidence: `build/installation-drift-2026-10-25/before.json`,
`candidate.json`, retained probe/update scripts and downloaded files. No raw task
response, credential contents or config values are retained in public evidence.

## Refused switches and correction

Two runtime-only switch attempts stopped **before moving the installation**
because the native-path active-process guard found the installed executable in
use. The installed hash stayed unchanged. Initial external process queries used
forward slashes while comparing raw CIM Windows paths, falsely reporting zero.
This was an audit error, not evidence of transient process exit. After path
normalization, four old-runtime MCP processes were observed (including frozen
launcher/child pairs). Do not force-stop them or keep retrying the switch.

Both prepared trees were moved, with validated exact paths, into the private
audit workspace as `paused-first-stage` and `paused-second-stage`. No material
files were deleted and no global staging tree remains from those attempts.

## One-shot handoff, not completed installation

A hidden one-shot updater was started and independently confirmed live as PID
12316 at this checkpoint. Its private `pending-update.json` says
`waiting_for_natural_exit`, with four active runtime processes. The JSON status
file alone is not proof of a live helper; verify the actual process on follow-up.
It waits until `2026-10-25T08:23:39Z` (16:23:39 Asia/Shanghai), then stops rather
than force-stopping anything or repeatedly scheduling more jobs.

Only after two idle checks may it invoke the scoped runtime sync: verify the old
and candidate hashes, prepare a sibling tree preserving existing extras, recheck
active processes, retain the complete previous directory under
`%LOCALAPPDATA%\Layman\runtime-backups`, and use caught-error rollback on a failed
switch. Updater-script hashes are checked before invocation. No `setup`, plugin
cache refresh, PATH/account/provider change, credential copy, API routing enable,
tag or public release. Config/state/launcher hashes are compared around the switch;
the helper cannot attribute concurrent edits.

The helper will write `sync.json` only after a real switch and `installed.json`
only after separate in-place version/preview/MCP checks. Timeout/error is not
success. Backups remain for recovery; no crash/power-loss/concurrent-installer
recovery or code signing is claimed. Overall goal remains active: this removes
a deployment gap only when actually completed, and establishes no token benefit.

## Terminal follow-up, 2026-10-26

The bounded handoff expired without switching the installation. Its final
private status is `timed_out_without_switch`, recorded at
`2026-10-25T08:23:44.0963738Z`, with four active runtime processes at that
checkpoint. This is a historical count, not a fresh process inventory.
On follow-up, helper PID 12316 was absent; `sync.json` and `installed.json`
were both absent. The actual PATH executable still hashes to
`bc4f670c0a6129a0ab69d4f3bc8b2285fc6401a017c61e417bbaf0d9c61465f5`.
No installation success or new backup is established.

No updater restart, deadline extension, force stop, candidate replacement or
installation retry was performed. The expired helper remains pinned to c35c5b7;
the separately verified newer c3c8f78 artifact does not change that contract.
The next installation step needs a maintenance window in which old Layman MCP
users have naturally exited, followed by fresh process/hash checks, a scoped
backup/switch and in-place acceptance. Until then, repository verification does
not mean the owner's running plugin uses the new runtime. This is an unfinished
deployment gate, not a token-saving claim or completion of the overall goal.
