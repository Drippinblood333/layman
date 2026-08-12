# Changelog

## 1.0.0 - Unreleased

- Reframed Layman as a Codex optimization and execution layer for beginners and developers.
- Added `$layman-status` and bounded, content-free project-stage inspection.
- Added `layman status`, `layman plan`, and `layman run` outcome-oriented entry points.
- Added minimal workflow/module selection so context, safety, verification, and routing are loaded only when relevant.
- Unified the task-safety skill and local API router as Layman.
- Added the `layman` CLI while retaining the `layman-router` compatibility alias.
- Added Plus/API capability separation, guided setup, background lifecycle commands and non-destructive v2 data migration.
- Added a unified Codex plugin with `$layman`, `$layman-status`, `$layman-auto`, and `$layman-router` skills.
- Added Experimental `$layman-auto` routing through an existing ChatGPT login, with no API-key fallback.
- Added adaptive file-reading, tool-output, final-answer and native compaction budgets.
- Added opt-in exact context deduplication for automatic API requests and privacy-minimized optimization metrics.
- Added opt-in GPT-5.6 stable-prefix caching with caller-marked API blocks, local cache read/write visibility, and stripping of Layman-only metadata before upstream forwarding.
- Updated GPT-5.6 standard pricing to the official 2026-07-30 rates and added 272K-threshold long-context cost estimation.
- Made Windows Codex discovery probe real executability and fall back to healthy VS Code/Cursor bundled CLIs when wrappers are broken.
- Made uninstall remove the Codex plugin and local marketplace before optional data purging.
- Raised pytest, pytest-asyncio, PyInstaller and Pillow development floors after the 2026-08-12 OSV audit found fixed vulnerabilities in the previous pytest/Pillow range.
- Updated release workflows to current action majors pinned to full commit SHAs, added an OSV dependency-audit gate, and enabled weekly Dependabot updates for Python and GitHub Actions.
- Restricted automated release publishing to the version-aligned `v1.0.0-rc.*` candidate series and final `v1.0.0` tag.
- Made the clean release job install and validate runtime dependencies before generating the resolved-version SBOM.
- Expanded the CI secret scan from selected public directories to the complete checked-out source tree.
- Refreshed the hashed runtime lock, made release builds consume it strictly, and expanded the SBOM from direct dependencies to the complete locked runtime set.
- Bundled the complete local Codex marketplace inside wheel and source distributions so clean package installs can run `layman setup`.
- Made setup create an explicitly configured new `CODEX_HOME` before its first Codex probe.
- Added wheel and sdist clean-install smoke checks to the Windows, macOS and Linux CI matrix.
- Replaced the retired macOS Intel runner label and added standalone setup/doctor/purge smoke checks to all five platform builds.
- Recorded explicit `setup --skip-plugin` state so fresh skipped-plugin installs can purge without Codex, while repeated or legacy states keep conservative cleanup protection.
- Staged a flat, allowlisted GitHub Release asset set whose checksum names exactly match downloaded asset names.
- Added a 30-task, 60-call direct-versus-Layman paired benchmark with hidden validation.
- Published its negative result: Layman improved accepted quality by one task but increased median total and output tokens, so optimization remains Experimental.
- Fixed the release calibration at 18 synthetic cases and 36 paired ChatGPT Plus calls.
- Added standalone builds, cross-platform CI, release checksums, SBOM, recovery and public contribution materials.
- Made one-line installers verify `SHA256SUMS.txt` before extracting release archives.
- Added an architecture record and third-party provenance policy; no competitor source is vendored in 1.0.0.

The API routing layer is Beta in 1.0.0 until a release-grade live API benchmark exists.
