# Installation and size baseline — 2026-10-10

This is a bounded read-only measurement of CI/local artifacts and current installer instructions, not a fresh local build, a public download test, or evidence of an installed user profile's size.

## Measured artifacts

### Latest verified five-platform checkpoint

Source `b82380d6ca5f6d6f4589ac4d054c4dccbd8633d7` passed all ten validation
jobs in [run 38056056295](https://github.com/Drippinblood333/layman/actions/runs/38056056295).
Downloaded its existing `release-assets` artifact (ID `11672041279`, outer
GitHub transport archive 117,836,976 bytes) once, without running or installing
any contained executable. The ignored local directory is
`build/ci-b82380d-size/release-assets`.

The following ZIPs are the assembled candidate release files inside that outer
artifact, not GitHub's per-platform transport archives. They have not been
published as public release downloads. Expanded bytes are the sum of file sizes
inside each ZIP, not actual installed-profile or filesystem allocation sizes.

| Platform | Candidate ZIP bytes | Expanded file bytes | Executable bytes |
| --- | ---: | ---: | ---: |
| Windows x64 | 17,074,588 | 17,389,307 | 17,253,472 |
| macOS x64 | 17,091,382 | 17,331,442 | 17,195,664 |
| macOS arm64 | 16,125,000 | 16,405,716 | 16,269,936 |
| Linux x64 | 34,282,467 | 34,590,450 | 34,454,672 |
| Linux arm64 | 32,997,149 | 33,302,132 | 33,166,352 |

Each ZIP has 32 files and records 24 locked runtime dependencies (direct plus
transitive). The executable accounts for more than 99% of expanded bytes on
every platform. This locates the size budget in the bundled executable, not
small documentation/skill files; it does not identify which embedded component
can safely be removed or explain cross-platform differences. A lean build must
preserve the required CLI/MCP/runtime behavior and license evidence.

All five ZIP SHA-256 values match the assembled `SHA256SUMS.json`; ZIP CRC checks
pass, and executable SHA-256 values match both `BUILD.json` and its digest-checked
bundle audit. Archive digests, in table order:

```text
windows-x64  42b4fc79904434a4d40a020a6168dcfc8fc1124bc6901937aca98b5cf9b479e3
macos-x64    a5bbd20466a6b23ca812280bbe3fc53a655dc222746fee5ca6747c1ed79b48f2
macos-arm64  8207a3893c33a6776b0378cd7dfbcf33be61d551a58a3c5828108a27a6a3de96
linux-x64    16ff8b8033ce555136f1e199265ffabf57c4758125852e63b910b17f9d329ea6
linux-arm64  cc055a67be4f557339003345ca04c6654e3e04706664b34a70f9e14eb6caf19b
```

Windows candidate ZIP size is 16.28 MiB, expanded files 16.58 MiB. These measured
values are baselines, not a demonstrated size reduction or token saving. No new
build, model execution, installation replacement or publication was performed.
Cold-start extraction space, installed profile size, user-data growth and public
onboarding remain unmeasured. Hash agreement is integrity evidence within this
CI artifact, not independent publisher identity or code signing.

### Historical Windows checkpoint

Source `eca27229ba70d0578c6f2fef317516e14163fad9` passed all ten validation
jobs in [run 38044677991](https://github.com/Drippinblood333/layman/actions/runs/38044677991);
publication was skipped. Downloaded only its Windows x64 CI artifact (ID
`11666538086`, GitHub artifact archive size 17,397,196 bytes), without executing
or installing it. This archive size is GitHub's transport size, not a public
installer or release download size.

- Executable: **17,256,040 bytes / 16.46 MiB**.
- Extracted artifact directory: **17,391,188 bytes, 32 files**.
- Executable SHA-256:
  `85add6dfb672170ff3ec625e266144ff48ef77eb28015b3335adb77d449dff1b`,
  matching its `BUILD.json` bundle-audit executable hash.
- Difference from historical hosted `abe6c52`: +40,185 executable bytes,
  approximately **+0.23%**, not a reduction or a controlled same-source build
  comparison. These measurements do not attribute the difference to a feature.

The candidate remains under ignored `build/ci-eca2722-size/windows-x64`.
Other-platform extracted sizes, cold-start extraction footprint, installed
profile size and user-data growth remain unmeasured. No full local regression or
fresh lifecycle smoke was repeated for this read-only size measurement.

### Historical measurements

| Artifact | Exact bytes | Interpretation |
| --- | ---: | --- |
| Windows executable from hosted source `abe6c52` | 17,215,855 | 16.42 MiB; downloaded candidate previously passed isolated lifecycle smoke |
| Its complete artifact directory (32 files) | 17,349,601 | Executable plus runtime/build/license evidence; not the installed user profile or temporary extraction footprint |
| Existing locally built upgraded-toolchain executable | 17,284,502 | Historical build, not a same-source controlled comparison |
| Its complete artifact directory (32 files) | 17,418,714 | Historical artifact-directory measurement only |

The historical hosted executable SHA-256 was rechecked: `5c0512a17dc486cd0845a9409d353759d153f1eb90aaa1db2697a410f42cff03`, matching the previously documented downloaded candidate. No artifact or user installation was modified. MiB means 1,048,576 bytes. These historical rows alone establish neither current-source nor other-platform sizes; the newer Windows measurement is separately reported above. Cold-start extraction footprint and user-data growth remain unmeasured.

## Default installation and first use

The Windows installer downloads the platform archive and checksum manifest, verifies before extraction, copies the executable, updates the user PATH unless disabled, and invokes setup unless disabled. The documented standalone path does not require a separately installed Python. Public download usability remains blocked by the absence of an owner-approved published release; source/CI delivery is not a public release.

The current package has seven declared direct Python runtime dependencies. They support the existing API, configuration and validation surfaces; removal without a feature/compatibility audit is not justified. The build excludes multiple development/presentation packages and bundles no LLMLingua, Headroom ML model or RTK executable by default. A small optional skill ZIP is not a feature-equivalent replacement for the complete CLI/MCP/runtime.

An actual onboarding flaw was found in `INSTALL.md`: the normal Plus first-use section offered an executable 36-call calibration before the user's own task. This is unnecessary for setup and risks spending subscription allowance without delivering a user outcome. The corrected default sequence is login/status checks, a zero-model task preview, then the user's actual task. Developer calibration remains available in a separate section requiring explicitly scoped cumulative approval.

## Verification and next measurement

Both local Markdown file links in the edited installation document resolve; instruction-flow inspection, whitespace validation and release secret scanning pass. No model call, installation replacement, dependency change or new full regression run was needed for this documentation-only correction. Before choosing a size reduction target, measure the latest verified artifacts on each supported platform and compare feature-equivalent builds. Only add an optional compression adapter after documenting its incremental download/runtime cost and real supported execution path.
