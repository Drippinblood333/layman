# Layman internal v3 / public 1.0 release checklist

Updated: 2026-08-12

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

- [x] The current 146-test unit/integration suite passes locally.
- [x] 300-case deterministic routing matrix passes.
- [x] 401, 429, 5xx, timeout, empty stream and interrupted stream paths are covered.
- [ ] Fresh fingerprinted 18-case/36-call Plus calibration is complete for the current release candidate; the 2026-07-16 historical run completed without execution errors but cannot close this gate.
- [x] 30-task/60-call token benchmark completed; the savings gate failed and the negative result is published.
- [x] GPT-5.6 model identifiers, reasoning efforts and 2026-07-30 short/long-context standard prices match current official documentation.
- [x] The installed dependency tree passes `pip check`; the 2026-08-12 OSV audit reports no known vulnerabilities after upgrading pytest and Pillow.
- [x] Strict hashed runtime installation and the 125-test pre-audit suite passed under a clean Python 3.14 environment; the final 146-test suite passed in the primary Python 3.14.3 environment, and the earlier 90-test baseline passed under independent Python 3.12.13. Python 3.11 remains in hosted CI.
- [x] CI uses current action majors pinned to full commit SHAs and runs `pip check`, OSV audit, tests, Python package build/install smoke checks, static analysis, plugin validation, whole-checkout secret scanning and a digest-pinned Docker build/health smoke; Dependabot covers Python and GitHub Actions.
- [ ] Human semantic-quality scoring is complete.
- [ ] macOS and Linux CI runs are green on the public repository.
- [ ] Live API benchmark exists; until then API routing remains Beta.

## Phase 3 — No-code installation

- [x] Windows x64 standalone executable builds and runs without Python.
- [x] Isolated setup installs a durable Codex marketplace and the Layman 1.0 plugin.
- [x] Windows setup, repeated setup, doctor and clean uninstall pass with a Chinese/space-safe temporary path.
- [x] Uninstall removes the Codex plugin and marketplace before `--purge-data` deletes the local marketplace files.
- [x] Cross-platform PyInstaller matrix and release packaging workflow exist.
- [x] The five-platform standalone matrix uses currently documented GitHub runner labels and runs help/setup/doctor/purge lifecycle smoke checks without requiring an API key or Codex installation.
- [x] Setup records an explicitly skipped plugin so uninstall can purge data without Codex while older or managed-plugin states remain conservative.
- [x] Release ZIP, wheel, sdist, hash-locked runtime requirements, checksums and a 24-component Python dependency SBOM build locally; standalone ZIPs separately inventory embedded CPython/PyInstaller components, include digest-checked license texts, and bind a distribution-level PyInstaller/EXE audit to each executable. The SBOM passes the official CycloneDX 1.5 schema.
- [x] Fresh virtual environments independently install the wheel and sdist, verify the bundled plugin hashes, expose the CLI and pass `doctor`.
- [x] GitHub Release assets are staged as a flat allowlisted set with checksums that match their public filenames.
- [x] One-line installers require and verify `SHA256SUMS.txt` before extraction.
- [ ] macOS x64/arm64 and Linux x64/arm64 artifacts pass hosted CI.
- [ ] Published one-line installers are tested against an actual GitHub prerelease.

## Phase 4 — Public release

- [x] English and Chinese README files, illustrated GIF, MIT license and contribution guide exist.
- [x] Architecture and third-party provenance documentation exists; no competitor source is silently vendored.
- [x] Issue, feature and pull-request templates exist.
- [x] CI, security checks and release workflow exist.
- [x] The publishing job accepts only version-aligned `v1.0.0-rc.*` candidates and the owner-approved `v1.0.0` tag.
- [x] The clean release-assets job uses `--require-hashes`, validates the installed tree against the lock, and rejects drift before building the runtime SBOM.
- [x] An honest historical Plus calibration report exists; current-candidate calibration remains open.
- [x] Public GitHub repository exists under `Drippinblood333/layman`.
- [x] The public repository has Actions, Issues, private vulnerability reporting, secret scanning and push protection enabled; workflow token permissions default to read-only.
- [ ] The initial `main` branch is pushed and hosted CI completes successfully.
- [ ] Dependabot vulnerability alerts/security updates are enabled after the default branch exists.
- [ ] A `main` ruleset requires the verified hosted CI checks after their check names exist.
- [ ] `v1.0.0-rc.1` is tested by 5–10 invited users with no unresolved P0/P1 issue.
- [ ] Owner approves and publishes `v1.0.0`.
