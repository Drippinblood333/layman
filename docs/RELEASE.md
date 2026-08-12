# Release procedure

1. Verify official model identifiers, reasoning-effort support and API prices; update `price_version` with the effective date.
2. Run unit/integration tests, the 300-case matrix, routing analysis, release checks, plugin validation, Ruff and Bandit.
3. Preview and complete the fixed 18-case/36-call ChatGPT Plus calibration. Do not use API-dollar language for subscription results.
4. Build standalone programs on Windows x64, macOS x64/arm64 and Linux x64/arm64; smoke-test `--help`, `doctor`, setup and uninstall in clean environments.
5. Build the wheel, source archive and unified Codex plugin. Generate the locked runtime dependency/license manifest and CycloneDX SBOM. Every standalone ZIP must also include the exact CPython/PyInstaller component inventory, all dependency/runtime license texts and a final-executable bundle audit. CPython is pinned to 3.14.3 and uses the digest-pinned complete license from its official embeddable distribution on every host. The build rejects unmapped, ambiguous, version-mismatched or unreviewed frozen distributions, records the pinned PyInstaller hooks provenance, and binds the audit to the executable digest before generating SHA-256 manifests. Confirm the legacy v1 ZIP hash is unchanged.
6. Test Codex enable, repeated enable, disable, conflict handling and backup restore against a temporary `CODEX_HOME`.
7. Scan archives and fixtures for API keys, credentials, raw private prompts, project code and stored response text.
8. Publish `v1.0.0-rc.1` to 5–10 invited testers. Test the exact prerelease with the `-Version v1.0.0-rc.1` PowerShell parameter or `LAYMAN_VERSION=v1.0.0-rc.1` shell environment variable documented in `INSTALL.md`; GitHub `releases/latest` excludes prereleases. Do not create `v1.0.0` while a P0/P1 issue remains.
9. Re-run every gate after candidate fixes. Create public `v1.0.0` only after explicit owner approval.

API routing remains labeled Beta until a release-grade live API benchmark exists. Dashboard savings are counterfactual estimates; ChatGPT Plus results are subscription calibration, not an API invoice.
