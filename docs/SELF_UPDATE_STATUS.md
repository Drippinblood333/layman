# Project update status

Updated: 2026-10-09

## Verified checkpoint

Code commit `abe6c52ada2110cdabf72a84d3003b1966f202f1` passed all nine jobs in [CI run 37823153836](https://github.com/Drippinblood333/layman/actions/runs/37823153836): Windows/macOS/Linux tests, five standalone build and installation lifecycle jobs, and Docker. The current suite contains 189 router tests and 41 adaptive-reasoning harness tests (230 total). Hosted checks include dependency vulnerability auditing, distribution installation, static analysis and secret scanning.

Automatic routing now uses GPT-6 Luna / GPT-6.1 Sol / GPT-6 Astra with low / medium / high reasoning respectively. Output verbosity and output caps are configured to limit unnecessary generation. These controls are implemented, but measured token savings and task-quality equivalence are not yet established.

## Continuing updates

### Request validation follow-up

The output-options audit reproduced malformed `text` values causing explicit-model crashes or silent replacement in automatic mode. The API now returns a clear HTTP 400 before contacting the upstream model. Eighteen regression cases cover five malformed shapes across automatic, configured-explicit and custom-explicit models, plus preservation of valid format and verbosity options. The updated suite passes 189 router tests and 41 adaptive harness tests (230 total), lint and secret scanning locally and in the hosted three-platform matrix. The checkpoint above includes this code change.

### Local installation drift

A zero-call dry run on 2026-10-09 found the installed `layman` executable still selecting `gpt-5.6-luna`, with a 2,000-token final-answer target and a 4,000-token tool-output limit. This differs from the updated source defaults. A repository push does not replace an already installed executable or refresh the Codex plugin cache. Local installation synchronization is awaiting the owner's choice; preserve an old-installation backup, account configuration and data when performing it. The bundled `layman-auto` instructions now name the configured routes and current GPT-6 defaults rather than the old Terra/Sol presets.

### Downloaded Windows candidate verification

The Windows x64 artifact downloaded from [CI run 37823153836](https://github.com/Drippinblood333/layman/actions/runs/37823153836), code commit `abe6c52`, passed the local isolated standalone smoke: setup with plugin skipped, doctor, planning, zero-call dry run, HTTP health, MCP tools and clean uninstall. Its executable SHA-256 is `5c0512a17dc486cd0845a9409d353759d153f1eb90aaa1db2697a410f42cff03`, matching `BUILD.json`. Health reported all three GPT-6 routes and the 2026-10-09 price version. The artifact is staged under `build/ci-abe6c52/windows-x64`; the existing user installation was not replaced. Temporary smoke-test data was removed by the test's isolated uninstall and temporary-directory cleanup, with no user data removed. This does not replace an actual published-prerelease installer test.

An active Codex heartbeat checks this project daily at 09:00 Asia/Shanghai, subject to the local scheduler and device being available. It advances bounded, verifiable fixes and reports meaningful progress, failures or required decisions. Dependabot checks Python dependencies and GitHub Actions weekly. Neither mechanism guarantees unattended release approval or safe automatic adoption of every upstream change.

## Dependency self-update follow-up

Dependabot PR [#4](https://github.com/Drippinblood333/layman/pull/4) proposes five development-tool upgrades. Its historical three-platform failures occurred in the version-pin test: the test required literal `ruff==0.15.21`, rejecting the proposed exact `ruff==0.16.8` pin. The test now validates the actual reproducibility contract instead of one obsolete version: each required quality tool must have one unconditional exact version requirement, with no ranges, wildcards, URLs or duplicate declarations. Ten regression cases verify acceptance of updated exact pins and rejection of weakened declarations. The complete local router and adaptive harness suites pass 240 tests after this change.

The five upgrades have now been applied as a coordinated candidate on the current branch, without merging the historical PR: PyInstaller 6.22.3, hooks 2026.7, build 1.6.1, Ruff 0.16.8 and Hatchling 1.32.3. Workflow pins and the standalone inventory match the dependency declaration; a new consistency test enforces that alignment. Upstream release records were checked: [PyInstaller](https://pyinstaller.org/en/v6.22.3/CHANGES.html), [hooks](https://github.com/pyinstaller/pyinstaller-hooks-contrib/releases/tag/v2026.7), [build](https://github.com/pypa/build/releases/tag/1.6.1), [Ruff](https://github.com/astral-sh/ruff/releases/tag/0.16.8), and [Hatchling](https://github.com/pypa/hatch/releases/tag/hatchling-v1.32.3).

The complete local suite passes 241 tests and the existing local linter/secret scan. Installing the new development tools locally failed with incomplete network responses, including a cache-free official-PyPI retry; those tests therefore do not prove execution under the upgraded tools. Fresh hosted tests, wheel/sdist installations and five-platform standalone builds are required before treating this candidate as verified. Runtime hash locks and artifact integrity checks remain unchanged; the user's installed executable has not been replaced.

The local download limitation was subsequently resolved by downloading complete wheels without the failing metadata-first path and comparing every wheel SHA-256 to its official PyPI release record before installation. All five updated tools and the build backend's two required dependencies are installed in the project virtual environment; `pip check` passes. Under the updated tools, 241 tests, the 300-case routing verification, Ruff 0.16.8, Bandit and secret scanning pass. Wheel and sdist builds and clean-install smoke tests pass; PyInstaller 6.22.3/hooks 2026.7 also builds a Windows standalone candidate that passes isolated lifecycle, HTTP and MCP smoke tests at `build/standalone-gpt6-upgraded/windows-x64`.

Hosted run [37824537148](https://github.com/Drippinblood333/layman/actions/runs/37824537148) passed all five platform builds and Docker but failed all three test jobs at the expanded Ruff checks. Ruff 0.16 expands its default rule set ([upstream migration guide](https://astral.sh/blog/ruff-v0.16.0)). The follow-up applies safe import/type-annotation cleanups, explicitly marks intentional regex concatenation, and documents narrow compatibility exceptions for existing validation errors and fail-closed benchmark boundaries. The root lint policy adds the former `E4`, `E7`, `E9`, and `F` checks to the new defaults and targets Python 3.11, so upgrading does not silently discard the old checks. Fresh hosted validation of this follow-up remains required.

The Linux test job in [follow-up run 37825669212](https://github.com/Drippinblood333/layman/actions/runs/37825669212) then identified only `EXE001`: twelve checked helpers had shebangs but lacked Git executable permissions. Windows does not enforce this POSIX check. All seventeen tracked shebang-bearing Python helpers under `scripts` and `evals` now have mode `100755`, including five additional helpers found by the regression audit. A portable test checks the Git index rather than Windows filesystem permission emulation. The full local suite now passes 242 tests and the updated linter; hosted verification of the permission fix remains pending. No production application behavior was changed by this follow-up.

## Remaining public-release gates

- Fresh release-candidate Plus calibration and human semantic-quality scoring.
- Explicit approval before paid API calibration. No live model benchmark was executed in this update batch.
- Complete six-arm adaptive comparison: local Codex CLI 0.160.0 passes zero-call preflight for five arms but does not expose Luna `none`. A five-arm subset cannot close the six-arm gate.
- Published prerelease installer checks and 5–10 invited testers, with no unresolved P0/P1 issue.
- Owner approval before a release tag or final public release.

The full adaptive protocol reserves a counterfactual API-cost ceiling of USD 286.35 including retries and judges. This is not actual expenditure, a subscription bill, or measured savings. See the benchmark protocol for its approval and budget controls.
