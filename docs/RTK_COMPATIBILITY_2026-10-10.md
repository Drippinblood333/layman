# Optional RTK compatibility check

Date: 2026-10-10. Decision: **do not automatically integrate or bundle RTK yet**.

This is a zero-model Windows subprocess smoke, not a task-token benchmark, an
installation test, or proof of Codex hook compatibility.

## Verified candidate

- Official release: [RTK v0.51.0](https://github.com/rtk-ai/rtk/releases/tag/v0.51.0).
- Windows x64 ZIP: 4,579,791 bytes; SHA-256
  `1623e9b45d28b15122d69e7314776e1123a804224885ce07e7182fb40080f05c`.
- Release API digest and separately verified official checksum list agreed.
- Extracted executable: 10,285,056 bytes; reports `rtk 0.51.0`.
- Download/extraction stays in ignored `build/rtk-integration-v0.51.0-20261010`.
  Nothing was added to PATH, default distribution, user installation or hooks.

The candidate's approximately 9.81 MiB executable would be extra default payload;
there is no demonstrated whole-task benefit justifying that addition.

## Bounded procedure and observations

Run a child Python command directly, then the identical argv under `rtk test`.
Both use `subprocess.run(..., capture_output=True, timeout=20)` without a shell.
Only synthetic text is supplied. Set child environment overrides:

```text
RTK_TELEMETRY_DISABLED=1
RTK_RECALL=0
RTK_TEE=0
RTK_SUPPRESS_HOOK_WARNING=1
RTK_DB_PATH=<absolute ignored candidate directory>/synthetic-tracking.db
```

The [pinned tracking implementation](https://github.com/rtk-ai/rtk/blob/v0.51.0/src/core/tracking.rs)
prioritizes `RTK_DB_PATH`; the
[pinned configuration implementation](https://github.com/rtk-ai/rtk/blob/v0.51.0/src/core/config.rs)
supports disabling recovery through these environment overrides. No global
configuration was written; existing configuration may still be read, so this is
not a fully hermetic configuration test.

| Synthetic fixture | Direct / RTK exit | Raw / filtered bytes | Failure marker |
| --- | --- | --- | --- |
| 20 `test_synthetic_N PASSED` lines, then `20 passed in 0.01s` | 0 / 0 | 530 / 153 | Not applicable |
| Same passing lines, then failure marker | 1 / 1 | 578 / 201 | Retained |
| Same passing lines, then failure marker | 7 / 7 | 578 / 201 | Retained |
| Failure marker first, then 20 cleanup lines | 7 / 7 | 598 / 164 | **Dropped** |

Exact failure marker: `FAILED test_synthetic_failure - AssertionError: expected 42, got 0`.
The cleanup fixture prints that line, then `cleanup synthetic line N` for N=0..19,
then exits with 7. RTK returned `OUTPUT (last 5 lines)` containing cleanup lines
15..19, but not the failure. This exercised a generic-output fallback, not a
supported test runner's dedicated parser; it does not establish that all RTK
parsers lose failures. It does establish that blanket wrapping of arbitrary
commands is unsafe for Layman's verification evidence.

## Acceptance consequence

Keep RTK optional and unintegrated. Any later narrow adapter needs explicit
supported-command selection, preservation of essential failure evidence and a
bounded raw-output fallback. Native Codex hook behavior, other platforms and real
task quality remain unverified. RTK's output estimates and these byte counts must
not be reported as whole-task model-token savings. No model evaluation budget was
spent or extended in this check.
