# Installation and size baseline — 2026-10-10

This is a bounded read-only measurement of CI/local artifacts and current installer instructions, not a fresh local build, a public download test, or evidence of an installed user profile's size.

## Measured artifacts

### Latest verified Windows checkpoint

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
