# Windows standalone offline acceptance — 2026-10-18

Downloaded `layman-windows-x64` artifact **12133912340** from successful
[CI 39120916701](https://github.com/Drippinblood333/layman/actions/runs/39120916701).
The artifact API independently maps it to source
`f11e326f96bb5f6b438ca9c68103e2c30cca6676`.

- GitHub archive size: 17,415,408 bytes.
- GitHub-reported archive digest:
  `5ae33e28d461a677e025657c10fa213980fb596d328d59f26df49db613a0fa46`.
  This is reported provenance, not an independently recomputed archive digest;
  the download tool extracted the archive without retaining it for this check.
- Extracted executable: **17,273,565 bytes** (about **16.5 MiB**).
- Locally computed executable SHA-256:
  `46fd530532761deedf46ee63a08540f98c78427ca3612187e1777da77f189521`,
  matching `BUILD.json`.
- All three linked runtime/component/audit metadata hashes matched their files.
  These internal links are consistency checks, not an independent signature.

## Actual binary checks

The frozen executable, not the source module, ran in an isolated Chinese/spaced
workspace and profile under ignored `build/ci-f11e326/`. Child PATH contained only
Windows System32; Codex/API/Layman inherited control variables were removed and
the test's own Layman/Codex homes were explicitly isolated. The Python test driver
was used only to orchestrate subprocesses; the binary did not require Python on
its PATH. User configuration SHA-256 was checked before/after without retaining
its contents. No installed executable or user configuration was replaced.

Passed:

- `plan --help` exposes `--brief`.
- Chinese stdin task produces valid UTF-8 full JSON and read-only brief guidance.
- Every full-plan next step, acceptance criterion and stop condition appears in
  the brief output; its permission and no-execution notice remain present.
- A vague Chinese task displays clarification and `plan-first` rather than
  implying execution has started.
- Offline planning creates no Layman installation state.
- Default setup with no discoverable Codex exits 1 with prerequisite guidance,
  leaves no Layman home and writes no Codex config.
- Real user config hash unchanged. No model invocation or API call was requested.

Private controller and machine-readable result remain in the ignored build
directory; no raw task/answer telemetry or credentials were added to the repo.
No new build, test-suite rerun, release tag or formal publication was requested.

## Limits

This is the current Windows host, not a clean OS, signed installer or all-platform
test. Clipboard GUI input, plugin installation with a real CLI, ChatGPT execution,
download installer and update/uninstall are outside this bounded batch. Current
binary size is measured, not a claim of size reduction. CLI-output bytes do not
prove model-token/fee savings or same-quality coding improvements. Main's separate
automatic CI 39121223805 was still in progress when checked, not assumed green.
