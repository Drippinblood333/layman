# Layman internal v3 / public 1.0 release checklist

Updated: 2026-07-17

## Phase 1 — Unified product

- [x] Public product and command are named Layman / `layman`.
- [x] `layman-router` remains a compatibility alias.
- [x] Unified Codex plugin contains `$layman`, `$layman-status`, `$layman-auto` and `$layman-router`.
- [x] Project status distinguishes repository evidence from verified release readiness.
- [x] Task planning selects only relevant workflow, context, routing, safety, output and verification modules.
- [x] Plus/API capability separation is explicit.
- [x] Setup, lifecycle, dashboard, report and uninstall commands exist.
- [x] Legacy v2 data migration copies without deleting the source.
- [x] Legacy v1 ZIP hash remains unchanged.

## Phase 2 — Validation

- [x] All 68 unit/integration tests pass locally.
- [x] 300-case deterministic routing matrix passes.
- [x] 401, 429, 5xx, timeout, empty stream and interrupted stream paths are covered.
- [x] Fixed 18-case/36-call Plus calibration completed with 36 successes and no stored answer text.
- [x] 30-task/60-call token benchmark completed; the savings gate failed and the negative result is published.
- [ ] Human semantic-quality scoring is complete.
- [ ] macOS and Linux CI runs are green on the public repository.
- [ ] Live API benchmark exists; until then API routing remains Beta.

## Phase 3 — No-code installation

- [x] Windows x64 standalone executable builds and runs without Python.
- [x] Isolated setup installs a durable Codex marketplace and the Layman 1.0 plugin.
- [x] Windows setup and doctor smoke tests pass with a Chinese/space-safe temporary path.
- [x] Cross-platform PyInstaller matrix and release packaging workflow exist.
- [x] Release ZIP, wheel, sdist, checksums and SBOM build locally.
- [x] One-line installers require and verify `SHA256SUMS.txt` before extraction.
- [ ] macOS x64/arm64 and Linux x64/arm64 artifacts pass hosted CI.
- [ ] Published one-line installers are tested against an actual GitHub prerelease.

## Phase 4 — Public release

- [x] English and Chinese README files, illustrated GIF, MIT license and contribution guide exist.
- [x] Architecture and third-party provenance documentation exists; no competitor source is silently vendored.
- [x] Issue, feature and pull-request templates exist.
- [x] CI, security checks and release workflow exist.
- [x] Honest Plus calibration report exists.
- [ ] Public GitHub repository is created after owner approval.
- [ ] `v0.9.0-rc.1` is tested by 5–10 invited users with no unresolved P0/P1 issue.
- [ ] Owner approves and publishes `v1.0.0`.
