# Release evidence — 2026-08-12

This snapshot records verified local evidence and keeps external release gates separate. It does not declare Layman 1.0 generally available.

## Local automated gates

- 87 unit and integration tests passed.
- The 300-case deterministic routing matrix, release checks, legacy v1 hash check, public plugin manifest/MCP/skill validation, Ruff, Bandit and release secret scan passed.
- The installed dependency tree passed `pip check`. An OSV audit initially identified fixed 2026 advisories in Pillow 11.3.0 and pytest 8.4.2; after raising the project floors and upgrading to Pillow 12.3.0 and pytest 9.1.1, the audit reported no known vulnerabilities.
- CI was updated to the current major releases of checkout, setup-python, artifact upload/download and release publishing actions, pinned to verified full commit SHAs. The three-platform test job now builds and clean-installs both Python distributions in addition to `pip check`, OSV audit, static analysis and release validation; Dependabot checks Python and GitHub Actions weekly.
- The Windows x64 standalone executable built with PyInstaller 6.22.0 on Python 3.14.3.
- Wheel, source archive, Codex plugin ZIP, Windows ZIP, CycloneDX 1.5 SBOM and SHA-256 manifests built locally.
- Fresh virtual environments installed the wheel and sdist independently. Both exposed the CLI, passed `doctor`, and contained all 19 bundled marketplace/plugin files with hashes matching the repository sources.
- All 19 entries in `SHA256SUMS.json` were rehashed successfully; the SBOM contains seven dependency components.
- The public-release staging step produced 13 allowlisted payload assets plus two checksum manifests at one flat directory level. Platform ZIP validation rejects missing executables, incorrect `BUILD.json` metadata and incomplete five-platform tagged releases.
- Release publishing is limited to `v0.9.0-rc.*` candidates and the owner-approved `v1.0.0` tag; unrelated `v*` tags cannot invoke the publishing job.

## Isolated Windows smoke test

The standalone executable was tested under a new ignored workspace path containing both Chinese characters and spaces. `LAYMAN_HOME`, `CODEX_HOME` and the router database were isolated from the user's normal configuration.

- `layman --help`: passed.
- First `layman setup --mode plus`: passed and installed `layman@layman-local`.
- Repeated setup: passed.
- `layman doctor`: passed.
- Codex plugin listing before uninstall: Layman installed and enabled.
- `layman uninstall --purge-data`: passed; Layman data was removed only after plugin and marketplace removal.
- Codex plugin and marketplace listings after uninstall: both passed with no Layman reference remaining.

The test also reproduced and fixed three Windows release blockers: automatic discovery previously selected a broken npm `codex.cmd` wrapper, purge uninstall previously left Codex pointing at a deleted local marketplace, and an explicitly configured new `CODEX_HOME` was not created before the first Codex probe. Layman now probes candidate executables with `--version`, can discover supported editor-bundled CLIs, creates an explicit Codex home when needed, and removes Codex references before deleting local data.

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
- macOS x64/arm64 and Linux x64/arm64 builds must pass hosted CI.
- Published one-line installers must be tested against an actual `v0.9.0-rc.1` prerelease.
- Human semantic scoring and invited-user acceptance by 5–10 testers remain open.
- Creating `v1.0.0` requires explicit owner approval after every blocking gate closes.
