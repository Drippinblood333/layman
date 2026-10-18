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

## Follow-up: actual frozen plugin setup and uninstall

Latest artifact **12135382197**, successful CI **39124123773**, source
`5495718bfdfca51d7f2a9c701bc5ec915460b199`, was downloaded separately. Its frozen
executable is **17,275,011 bytes**, SHA-256
`133569a662d4980fc83550059d1749cd82081a91e40026d28d597cb1284d29d7`.
Executable and all three linked metadata hashes matched `BUILD.json`; no binary
size reduction is claimed. Main's separate CI **39124387511** is now terminal success.

Actual `setup --mode plus` succeeded in a new Chinese/spaced, unsigned-in test
profile with explicit isolated Layman/Codex homes and no global Layman/Python on
child PATH. The pinned private **0.162.0-alpha.20** Codex CLI performed the native
marketplace/plugin registration. No user auth file was copied. The installed MCP
launcher pointed to this exact frozen executable with `mcp-server`, not a Python
module command; native cached launcher matched it exactly.

Starting that cached command actually initialized MCP, listed all three tools and
returned a Chinese read-only plan. Direct frozen `plan --brief` with Chinese UTF-8
stdin also passed. Non-UTF-8 Python environment overrides were supplied, but the
binary's internal encoding was not independently introspected; source regressions
and hosted Windows tests separately cover forced legacy text decoding.

Then actual `uninstall --purge-data` exited zero and removed only the test-created
owned Layman home, after checking its resolved target stayed under this batch's
isolated profile and its ownership marker. Native isolated caches/backups may
remain; downloaded files and fixed reports were retained. Real user config hash
was unchanged after setup/MCP and after uninstall; the downloaded executable hash
also stayed unchanged. No current user installation was replaced or model task
started. Private controllers/results: ignored `build/ci-5495718/`.

The [official marketplace registration guide](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli)
was searched/fetched before commands. This verifies the tested pinned CLI, not
all current/future plugin command versions; current documentation recommends the
desktop app for local plugin installation/testing. No desktop UI restart/load,
clean-OS installation, public download installer, live auth/execution or non-Windows
claim follows from this bounded native-CLI/frozen-package acceptance.
