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
- Added a 30-task, 60-call direct-versus-Layman paired benchmark with hidden validation.
- Published its negative result: Layman improved accepted quality by one task but increased median total and output tokens, so optimization remains Experimental.
- Fixed the release calibration at 18 synthetic cases and 36 paired ChatGPT Plus calls.
- Added standalone builds, cross-platform CI, release checksums, SBOM, recovery and public contribution materials.
- Made one-line installers verify `SHA256SUMS.txt` before extracting release archives.
- Added an architecture record and third-party provenance policy; no competitor source is vendored in 1.0.0.

The API routing layer is Beta in 1.0.0 until a release-grade live API benchmark exists.
