# First-use guidance delivery acceptance, 2026-10-26

## Exact delivery

Remote main was independently read as
`c3c8f78fa521c8666b26b4a430340ae6da5c0870`. Its
[main CI 40170575526](https://github.com/Drippinblood333/layman/actions/runs/40170575526)
completed successfully: three operating-system test jobs, five standalone
build jobs, Docker and combined release assembly passed. Publication skipped.
No tag or formal release was created in this batch.

This source includes the plain-language README introduction, safe offline
guidance for bare CLI invocation and resolved-workspace visibility in brief
plans. Historical local test results are recorded in SELF_UPDATE_STATUS;
they were not rerun solely to close delivery evidence.

## Downloaded Windows acceptance

Artifact `12589168369` (`layman-windows-x64`) came from exact-source
[validation CI 40170264102](https://github.com/Drippinblood333/layman/actions/runs/40170264102).
The old download process session was no longer observable. This is not treated
as a recovered clean download exit: acceptance instead checked the actual files.

- Executable: 17,276,805 bytes; SHA-256
  `e39eceb204e987c762b394adfdf3a437e7a77996772713e77e0d286f561e5396`.
- Executable digest matches BUILD.json; the three referenced inventory/audit
  digests and source runtime-lock digest match. Notices and licenses exist.
- Bare executable exits 0 with exactly three guidance lines, empty stderr and
  no echo of the private piped task. An absent config does not cause failure.
- A brief plan using relative `--cwd` resolves a Chinese/spaced directory and
  displays its absolute workspace before the next action, without execution or
  task-marker echo. Structured planning retains that workspace, read-only
  sandbox and `stores_task_or_code: false`.
- Isolated Layman/Codex homes remain absent and the owned workspace stays empty.
  Zero real model generations; no owner runtime or updater changes.

Private reproducible verifier and report:
`build/first-use-guide-artifact-2026-10-25/verify.py` and `result.json`.
The verifier refuses overwriting an existing report. No redownload or rebuild
was needed this batch.

## Remaining boundary

These are isolated frozen-executable smoke checks, not a fresh-OS installation,
authenticated model task, human usability trial or measured token improvement.
The owner still has the old runtime: the separate c35c5b7 updater timed out
without switching. See [the terminal installation evidence](LOCAL_RUNTIME_DRIFT_2026-10-25.md#terminal-follow-up-2026-10-26).
No automatic retry or forced shutdown was attempted. Formal release, independent
quality/fresh holdout acceptance and proven default token benefit remain open.
