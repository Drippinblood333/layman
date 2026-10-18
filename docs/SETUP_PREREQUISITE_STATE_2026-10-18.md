# Missing CLI setup prerequisite — 2026-10-18

Default setup previously wrote its mode/token/migration/managed-plugin state
before plugin installation discovered that no usable Codex CLI was available.
This could create a new Layman home or change an existing API installation's
mode and managed-plugin flag despite failing setup.

CLI setup now reuses the discovery result already produced by mode detection.
When plugin installation is requested and no executable was discovered, it exits
with installation/repair, offline-plan and explicit skip-plugin guidance before
reading/updating the Layman setup state or installing the plugin. No additional
CLI subprocess, dependency or model invocation is introduced. The guard checks
discovered executable presence, not login success: an unsigned-in CLI can still
install the plugin. Explicit skip-plugin behavior remains unchanged.

## Verification

- Two regression cases failed first: new home was created; existing state changed.
- A CLI-present/login-absent control passed before and after the fix.
- Lifecycle, CLI and MCP suites: **54 passed** after the change.
- Ruff, Bandit and whitespace checks passed.

This is not transactional setup. Detection may create `CODEX_HOME` if explicitly
configured. A CLI disappearing after discovery or a later plugin/configuration
failure can still leave partial setup work. Tests use isolated synthetic homes,
not the user's installation. No paid API, token-savings claim, release or installed
version replacement. Release secret scanning also passed. Source commit
`78fdaff7cb10f3bbd3fe2c365232d6fd0a3ef0b1` was pushed to
`codex/verify-setup-prerequisite` after one TLS handshake failure and a successful
retry. Exact [CI run 39120437908](https://github.com/Drippinblood333/layman/actions/runs/39120437908)
completed successfully with all ten validation jobs passed, without rerunning.
After a fresh fetch and ancestry check, remote main was fast-forwarded from
`841eaa5` to the exact verified SHA and independently confirmed with `ls-remote`.
No duplicate CI was dispatched or formal release requested. Main's automatic
push-triggered [run 39120729639](https://github.com/Drippinblood333/layman/actions/runs/39120729639)
subsequently completed successfully on this same SHA. This was read from the
terminal run state, not inferred from the earlier validation-branch gate.
