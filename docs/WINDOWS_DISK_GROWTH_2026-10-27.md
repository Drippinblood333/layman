# Windows temporary-runtime growth repair, 2026-10-27

## Diagnosis and approved scope

Read-only inspection found 14 `_MEI*` directories under the owner's Windows
Temp, each containing `layman_router` and `layman-bundle`: 138 files and
39,259,336 file bytes each, 549,630,704 bytes total (524.17 MiB). Installed
executable: 28,489,749 bytes; Layman state and the older router directory were
each below 1 MiB. This is an occupation snapshot, not a measured growth rate.

The build used PyInstaller `--onefile`. Its [documented operating mode](https://pyinstaller.org/en/stable/operating-mode.html#how-the-one-file-program-works)
extracts support files to a temporary directory; normal termination should remove
them, but crashes/forced termination can leave them behind. Individual historical
termination causes were not attributed. A version upgrade retaining onefile is
not by itself a repair of this mechanism.

The owner approved directory-based Windows installation, fixing new extraction
before recovering verified old residues, with no broad Temp cleanup or forced
termination of existing work. Log rotation and unrelated Codex data are out of
scope; no claim that all C: growth came from Layman.

## Implementation and validation

- Windows builds use `--onedir`, flattened to preserve `layman.exe` at the ZIP
  root beside `_internal/`. macOS/Linux retain their existing onefile packaging.
- Distribution auditing includes native extensions outside the executable,
  using the same dependency allowlist. No runtime dependency changes.
- Windows installer copies the support directory to the staged installation,
  replacing only its owned staged support tree rather than nesting directories
  or merging stale support files. Legacy onefile archives remain accepted.
- The standalone smoke isolates TEMP/TMP, runs three version starts, terminates
  one owned idle MCP test process and checks for runtime extraction during/after
  it and the normal lifecycle. No model task is submitted. Existing setup,
  doctor, planning, dry run, HTTP, MCP and isolated uninstall also pass.

The Windows-mode regression failed before the fix. Packaging and native installer
tests, including reinstall and rollback controls, then passed: **56 tests**.
The first full run used an in-repository test directory, invalidating an existing
test's assumption that its external-output fixture is outside the workspace;
55 tests passed and that assertion failed. With a fresh D: test directory outside
the repository, all 56 passed. No production validation was weakened to fix that
test-location issue. Scoped Ruff and `git diff --check` passed.

Local Windows package: **209 files / 34,533,917 bytes (32.93 MiB)**, including
support files and compliance inventories. Executable SHA-256:
`110b5ef02546d14703ec84364f2dc7f002628495611bef0e74077ed6e7bf6c03`.
This whole-directory measurement must not be compared as though it were only a
compressed onefile executable. Download ZIP size and cross-platform hosted
verification are not established by the local build.

## Actual installation and recoverable cleanup

A fresh process check found no running Layman. The scoped switch rechecked the
old executable hash, candidate identity, reparse-free trees and idle state;
copied/verified all 209 files; retained the complete old installation under
`%LOCALAPPDATA%\Layman\runtime-backups\pre-onedir-20261027-<transaction-id>`;
and verified installed file hashes, version and offline preview. Config, state
and cached MCP-launcher hashes were unchanged. No account/PATH/plugin refresh
or old updater restart. The prior expired updater remains historical evidence,
not the mechanism used for this separately authorized repair.

For each of the exact 14 old extraction paths: confirmed Layman markers,
unchanged count/bytes, no reparse points, no Layman process and exclusive-open
access to every file; copied to D:; checked every copied file SHA-256; rechecked
source hashes and inactivity; then removed only that validated C: directory.
All 14 completed, with zero `_MEI*` directories remaining at the final snapshot.
The checks are point-in-time safeguards, not an atomic guarantee against arbitrary
concurrent third-party changes. No owner process was force-stopped.

**549,630,704 file bytes of old temporary contents were removed from C:.**
Recovery copies remain on D:, so this is not whole-machine disk reclamation.
The new 32.93 MiB installation and one retained 27.17 MiB old-runtime backup are
separate retained costs; the temporary-content number is not net C: free-space
change or allocated-cluster measurement. A final PATH version invocation resolved
the new installed executable and exited without leaving a runtime process.

Private evidence under `build/onedir-disk-fix-2026-10-27/`:
`installed.json`, `recovered.json`, per-directory hash manifests,
`recovered-old-extractions/` and the scoped one-shot scripts. The initial recovery
report's aggregate was null due to PowerShell dictionary property measurement;
its original is retained as `recovered-original.json`. The corrected aggregate
is the independently recomputed sum of the 14 unchanged per-directory records;
cleanup was not rerun. Full paths remain private.

## Limits

This establishes the local Windows repair and recoverability, not a fresh-OS
installer trial, long-duration disk-growth rate, hosted release validation,
signed/public release, independent human acceptance or measured token savings.
There were zero real model generations. Other logs/caches may still grow; they
must be measured separately before expanding the repair.
