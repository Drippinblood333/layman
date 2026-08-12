# Release evidence — 2026-08-12

This snapshot records verified local evidence and keeps external release gates separate. It does not declare Layman 1.0 generally available.

## Local automated gates

- The current 149-test unit and integration suite passed in the primary Python 3.14.3 environment; the preceding 125-test suite also passed in a clean Python 3.14 environment installed from the hash-locked runtime set before the later bundle-audit and live-benchmark safety regressions were added.
- The 300-case deterministic routing matrix, release checks, legacy v1 hash check, public plugin manifest/MCP/skill validation, Ruff, Bandit and whole-checkout release secret scan passed.
- The installed dependency tree passed `pip check`. An OSV audit initially identified fixed 2026 advisories in Pillow 11.3.0 and pytest 8.4.2; after raising the project floors and upgrading to Pillow 12.3.0 and pytest 9.1.1, an audit reported no known vulnerabilities. The final local retry was blocked by the configured proxy disconnecting from `api.osv.dev`, so the hosted audit remains the current confirmation gate.
- CI was updated to the current major releases of checkout, setup-python, artifact upload/download and release publishing actions, pinned to verified full commit SHAs. The three-platform test job now builds and clean-installs both Python distributions in addition to `pip check`, OSV audit, static analysis, whole-checkout secret scanning and release validation. A separate Linux job builds the digest-pinned Python 3.14.3 Docker image from the hash-locked runtime set and health-smokes it; local Docker was unavailable, so that execution remains hosted evidence. Dependabot checks Python and GitHub Actions weekly.
- Current GitHub runner labels are used: `macos-15-intel` for Intel, `macos-15` for Apple Silicon and `ubuntu-24.04-arm` for Linux ARM. The latter is currently a GitHub Public Preview runner, so hosted execution remains an external gate.
- The Windows x64 standalone executable built with PyInstaller 6.22.0 and pinned pyinstaller-hooks-contrib 2026.6 on Python 3.14.3. Its final distribution audit mapped every collected file and reopened the EXE archive: exactly the 24 locked runtime distributions, Layman and PyInstaller were present; no unowned, ambiguous, version-mismatched or unreviewed distribution remained.
- Wheel, source archive, Codex plugin ZIP, Windows ZIP, hash-locked runtime requirements, CycloneDX 1.5 Python-dependency SBOM and SHA-256 manifests built locally. Direct build tools are version-pinned and every resulting artifact is checksummed, but byte-for-byte reproducibility across rebuilds is not claimed because build-tool transitives and archive timestamps are not fully normalized.
- Fresh virtual environments installed the wheel and sdist independently. Both exposed the CLI, passed `doctor`, and contained all 19 bundled marketplace/plugin files with hashes matching the repository sources.
- The hashed runtime lock installed cleanly under Python 3.14 and the independent bundled Python 3.12.13 runtime. The 125-test pre-audit suite passed under the clean Python 3.14 install; the earlier 90-test baseline passed under Python 3.12 together with `pip check` and `doctor`. Hash enforcement rejected inconsistent proxy/cache responses; a cache-free download matched the official PyPI hashes and passed. Python 3.11 remains a hosted-CI gate.
- All 51 entries in `SHA256SUMS.json` were generated from the rebuilt release tree; the manifest SHA-256 is `7B627C84DF97805F39E90D65AF5AE481DE368A254E3D9E6D2DEE0BC4457556D4`. The Windows ZIP is `FC548ADE80520A7A3D2F6E2AAB37DA4ECE621EE3963FB2ABABEC56997EE5EDD1`, and the executable is `5AEAE8D92537482D8F5FC54077FA5707D36430584CD5721A6F7577A57BA5F378`. The SBOM contains all 24 locked direct and transitive Python runtime components, every component version and purl was checked against `requirements.lock`, and the final JSON passed the official CycloneDX 1.5 schema. The Windows ZIP additionally contains 24 dependency license texts, the CPython 3.14.3 and PyInstaller 6.22.0 component/license records, and a digest-bound bundle audit; all 26 license-file digests, component manifests, audit and executable identity were validated.
- The public-release staging step produced 15 allowlisted payload assets plus two checksum manifests at one flat directory level. Platform ZIP validation rejects missing executables, incorrect `BUILD.json` metadata, missing or changed license texts, and incomplete five-platform tagged releases.
- Release publishing is limited to version-aligned `v1.0.0-rc.*` candidates and the owner-approved `v1.0.0` tag; unrelated `v*` tags cannot invoke the publishing job.
- The isolated release-assets job installs runtime dependencies from `requirements.lock` with `--require-hashes`, installs the local package without re-resolving dependencies, and runs `pip check`. The build then rejects any installed/locked version mismatch before generating the complete runtime SBOM.

## Isolated Windows smoke test

The standalone executable was tested under a new ignored workspace path containing both Chinese characters and spaces. `LAYMAN_HOME`, `CODEX_HOME` and the router database were isolated from the user's normal configuration.

- `layman --help`: passed.
- First `layman setup --mode plus`: passed and installed `layman@layman-local`.
- Repeated setup: passed.
- `layman doctor`: passed.
- Codex plugin listing before uninstall: Layman installed and enabled.
- `layman uninstall --purge-data`: passed; Layman data was removed only after plugin and marketplace removal.
- Codex plugin and marketplace listings after uninstall: both passed with no Layman reference remaining.
- The reusable standalone smoke gate also passed locally with no API key or plugin installation: help, Plus setup with `--skip-plugin`, state persistence, `doctor`, planning, dry-run execution, HTTP health, MCP initialize/list/plan/inspect, and `uninstall --purge-data`. The same gate is configured for all five standalone runner entries.

The test also reproduced and fixed four release blockers: automatic discovery previously selected a broken npm `codex.cmd` wrapper, purge uninstall previously left Codex pointing at a deleted local marketplace, an explicitly configured new `CODEX_HOME` was not created before the first Codex probe, and users who intentionally skipped plugin installation could not purge their isolated Layman data without a Codex CLI. Layman now probes candidate executables with `--version`, can discover supported editor-bundled CLIs, creates an explicit Codex home when needed, records whether plugin management was skipped, and removes Codex references before deleting local data whenever those references may exist. Repeated skip requests preserve managed state, while legacy state without explicit evidence remains conservative.

## Read-only GitHub settings audit

The empty remote repository is public and the authenticated owner has admin access. Issues and Actions are enabled; workflow tokens default to read-only, while the release job requests `contents: write` only for its publishing job. Private vulnerability reporting, secret scanning and push protection are enabled. The workflow itself pins all external actions even though repository-wide SHA enforcement is not currently required.

Dependabot vulnerability alerts and security updates are disabled. No ruleset or branch protection exists because `main` has not been pushed yet. Enabling those security settings and adding required CI checks after the first successful hosted run remain external configuration gates.

## Official OpenAI verification

The active model roles remain aligned with the current [GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/model-guidance?model=gpt-5.6): Luna for efficient high-volume work, Terra for balanced production work and Sol for frontier work. The configured `none` through `max` reasoning-effort vocabulary is supported.

Pricing metadata now uses the official [OpenAI API pricing table](https://developers.openai.com/api/docs/pricing), effective 2026-07-30. Per-million-token standard prices are:

| Model | Short input / cached / write / output | Long input / cached / write / output |
| --- | --- | --- |
| `gpt-5.6-luna` | $0.20 / $0.02 / $0.25 / $1.20 | $0.40 / $0.04 / $0.50 / $1.80 |
| `gpt-5.6-terra` | $2.00 / $0.20 / $2.50 / $12.00 | $4.00 / $0.40 / $5.00 / $18.00 |
| `gpt-5.6-sol` | $5.00 / $0.50 / $6.25 / $30.00 | $10.00 / $1.00 / $12.50 / $45.00 |

The estimator applies long-context rates to the full request when input exceeds 272,000 tokens. API routing remains Beta because no release-grade live API benchmark has been run.

## External gates still open

- The public GitHub repository exists, but it has no pushed default branch, workflow run, tag or release yet.
- The current release candidate needs a fresh fingerprinted 18-case/36-call Plus calibration; the July 16 records are historical only.
- The rewritten real-API runner safely supports a stateless/no-tool holdout, but no paid release-grade API calibration or human scoring has run; API routing remains Beta. State and tool cases are rejected before billing until real predecessor and deterministic tool-loop support exists.
- Dependabot vulnerability alerts/security updates and a required-check branch ruleset must be enabled after the initial branch and check names exist.
- macOS x64/arm64 and Linux x64/arm64 builds must pass hosted CI.
- The digest-pinned Docker build and health smoke must pass hosted CI.
- Published one-line installers must be tested against an actual `v1.0.0-rc.1` prerelease.
- Human semantic scoring and invited-user acceptance by 5–10 testers remain open.
- Creating `v1.0.0` requires explicit owner approval after every blocking gate closes.
