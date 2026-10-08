# Release evidence — 2026-08-12

This snapshot records verified local evidence and keeps external release gates separate. It does not declare Layman 1.0 generally available.

## Local automated gates

- The current local suite passes 171 router tests plus 41 adaptive-reasoning harness tests under Python 3.14.3. The preceding 149-test suite remains the last clean-install/hosted baseline; the older 125-test suite also passed in a clean Python 3.14 environment before later release and benchmark regressions were added.
- The 300-case deterministic routing matrix, release checks, legacy v1 hash check, public plugin manifest/MCP/skill validation, Ruff, Bandit and whole-checkout release secret scan passed.
- The installed dependency tree passed `pip check`. An OSV audit initially identified fixed 2026 advisories in Pillow 11.3.0 and pytest 8.4.2; after upgrading to Pillow 12.3.0 and pytest 9.1.1, the final hosted OSV audits on Windows, macOS and Linux reported no known vulnerabilities. A local retry remained unavailable because the configured proxy disconnected from `api.osv.dev`.
- CI was updated to the current major releases of checkout, setup-python, artifact upload/download and release publishing actions, pinned to verified full commit SHAs. The three-platform test job now builds and clean-installs both Python distributions in addition to `pip check`, OSV audit, static analysis, whole-checkout secret scanning and release validation. A separate Linux job builds the digest-pinned Python 3.14.3 Docker image from the hash-locked runtime set and health-smokes it; local Docker was unavailable, so that execution remains hosted evidence. Dependabot checks Python and GitHub Actions weekly.
- Current GitHub runner labels are used: `macos-15-intel` for Intel, `macos-15` for Apple Silicon and `ubuntu-24.04-arm` for Linux ARM. The complete hosted matrix passed on commit `67151cfcac637f9a0d541825ab3d0ee14e71b0c8` in [CI run 31622935570](https://github.com/Drippinblood333/layman/actions/runs/31622935570): three test jobs, five standalone build/lifecycle jobs and the digest-pinned Docker build/health job all succeeded.
- The Windows x64 standalone executable built with PyInstaller 6.22.0 and pinned pyinstaller-hooks-contrib 2026.6 on Python 3.14.3. Its final distribution audit mapped every collected file and reopened the EXE archive: exactly the 24 locked runtime distributions, Layman and PyInstaller were present; no unowned, ambiguous, version-mismatched or unreviewed distribution remained.
- Wheel, source archive, Codex plugin ZIP, Windows ZIP, hash-locked runtime requirements, CycloneDX 1.5 Python-dependency SBOM and SHA-256 manifests built locally. Direct build tools are version-pinned and every resulting artifact is checksummed, but byte-for-byte reproducibility across rebuilds is not claimed because build-tool transitives and archive timestamps are not fully normalized.
- Fresh virtual environments installed the wheel and sdist independently. Both exposed the CLI, passed `doctor`, and contained all 19 bundled marketplace/plugin files with hashes matching the repository sources.
- The hashed runtime lock installed cleanly under Python 3.14 and the independent bundled Python 3.12.13 runtime. The 125-test pre-audit suite passed under the clean Python 3.14 install; the earlier 90-test baseline passed under Python 3.12 together with `pip check` and `doctor`. Hash enforcement rejected inconsistent proxy/cache responses; a cache-free download matched the official PyPI hashes and passed. Python 3.11 remains a hosted-CI gate.
- All 51 entries in `SHA256SUMS.json` were regenerated from the current GPT-6 local release tree; the manifest SHA-256 is `580100D88B9CEC70076BEF44EF796998E6A854D046702C250EA1D8F239531553`. The Windows ZIP is `1BC731FD2728D52DE3F388DC033D3CE64B1C7A734F462BC782C3A07BDB1EB24F`, and the executable is `A5BC10124FCE912705A22F0BFC822F33E66DA4DDCD52B557921BF782149A638E`. The SBOM contains all 24 locked direct and transitive Python runtime components, every component version and purl was checked against `requirements.lock`, and the final JSON passed the official CycloneDX 1.5 schema. The Windows ZIP additionally contains 24 dependency license texts, the CPython 3.14.3 and PyInstaller 6.22.0 component/license records, and a digest-bound bundle audit; all 26 license-file digests, component manifests, audit and executable identity were validated.
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

## Public GitHub and hosted release gates

The public repository now has a pushed `main` branch. Issues and Actions are enabled; workflow tokens default to read-only, while the release job requests `contents: write` only for its publishing job. Private vulnerability reporting, secret scanning and push protection are enabled. Repository-wide Actions SHA pinning is required, and every current external action reference is a full commit SHA.

Dependabot vulnerability alerts and automated security updates are enabled. The active [`Protect main with verified CI`](https://github.com/Drippinblood333/layman/rules/20758059) ruleset blocks branch deletion and non-fast-forward updates, requires linear history, and requires the nine successful CI check contexts observed in run 31622935570. The repository owner has an explicit, auditable emergency bypass.

## Official OpenAI verification

The active route uses [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) for fast high-volume work, [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) for balanced work and [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) for the hardest work. Luna supports `none`; Astra and GPT-6.1 Sol reject `none`, and the configuration model now enforces that boundary. Automatic API requests also set low output verbosity for fast and balanced routes and medium verbosity for deep routes.

Pricing metadata uses the official [OpenAI API pricing table](https://developers.openai.com/api/docs/pricing), verified 2026-10-09. Per-million-token standard prices are:

| Model | Short input / cached / write / output | Long input / cached / write / output |
| --- | --- | --- |
| `gpt-6-luna` | $0.10 / $0.01 / $0.125 / $0.50 | $0.20 / $0.02 / $0.25 / $0.75 |
| `gpt-6.1-sol` | $2.00 / $0.10 / $2.50 / $10.00 | $4.00 / $0.20 / $5.00 / $15.00 |
| `gpt-6-astra` | $10.00 / $1.00 / $12.50 / $50.00 | $20.00 / $2.00 / $25.00 / $75.00 |

The estimator applies long-context rates to the full request when input exceeds 272,000 tokens. API routing remains Beta because no release-grade live API benchmark has been run.

The adaptive-reasoning v1 protocol defines 30 fresh holdouts and six GPT-6 model/effort arms. Offline validation and a zero-call dry run pass; the worst-case full execution plus semantic-judge reservation is $286.35. No paid call was made, and the production heuristic remains explicitly `heuristic_uncalibrated` until an approved run and human review establish a lower sufficient arm.

## External gates still open

- The public GitHub repository and protected default branch are live and hosted CI is green; no release tag or GitHub Release has been created.
- The current release candidate needs a fresh fingerprinted 18-case/36-call Plus calibration; the July 16 records are historical only.
- The rewritten real-API runner safely supports a stateless/no-tool holdout, but no paid release-grade API calibration or human scoring has run; API routing remains Beta. State and tool cases are rejected before billing until real predecessor and deterministic tool-loop support exists.
- Published one-line installers must be tested against an actual `v1.0.0-rc.1` prerelease.
- Human semantic scoring and invited-user acceptance by 5–10 testers remain open.
- Creating `v1.0.0` requires explicit owner approval after every blocking gate closes.
