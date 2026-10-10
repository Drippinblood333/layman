# Installation and size baseline — 2026-10-10

These are bounded artifact and isolated-runtime measurements, not a fresh local build, a public download test, or evidence of an installed user profile's size.

## Measured artifacts

### Current Windows initialized-runtime snapshot

Verified source `d510120386d400f26caab6f01ecd9075452c0bfc` passed all ten
validation jobs in [run 38060294327](https://github.com/Drippinblood333/layman/actions/runs/38060294327).
Downloaded its Windows x64 artifact once (ID `11672284115`, outer GitHub
transport 17,398,902 bytes) to ignored `build/ci-d510120-footprint/windows-x64`.
Executable SHA-256 `be493661175c539c6c1730a839fe48745115e2f4fb56176fe384f5289dc981ad`
matches `BUILD.json` and its digest-verified bundle audit before launch.

Launched only `mcp-server` in a newly created isolated fixture under that build
directory, with child-only `TEMP`, `TMP` and `LAYMAN_HOME` locations. Removed
model-provider/Layman overrides from the child's environment. Sent only the
local `initialize` handshake, not a tool invocation; the reply confirmed Layman
was initialized. No Codex login, setup, API request or model task was invoked.

| Observed logical file sizes | Bytes | Files |
| --- | ---: | ---: |
| Candidate artifact directory | 17,392,894 | 32 |
| Executable alone (included above) | 17,257,059 | 1 |
| Live initialized `_MEI` temporary extraction | 28,206,516 | 181 |

The artifact is 16.59 MiB and temporary extraction 26.90 MiB. Their combined
logical file sizes are 43.49 MiB, not a minimum free-disk requirement or actual
allocated-disk measurement. The temporary size was stable across two observations
after the initialization reply; it is not peak extraction/RAM usage or a cold-start
timing result. Normal stdin closure returned exit 0 and removed the temporary
extraction. The isolated Layman data-home directory was never created. The
candidate and empty fixture remain ignored; existing installations/configuration
were not replaced. Installed-profile growth, startup peaks and other platforms'
runtime extraction still need separate evidence.

### Five-platform pre-strip checkpoint

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

### Linux native-symbol size investigation

Read the existing Windows and Linux x64 executables' PyInstaller archives without
executing them. Windows' largest entries are the Python module archive
(5,723,712 stored bytes), Python DLL (2,719,317), Pydantic core (1,922,016),
OpenSSL crypto library (1,854,357) and SQLite (843,195). The module archive has
687 modules and no modules rooted in IPython, NumPy, pandas, matplotlib, Pillow,
pytest, setuptools, rich or tkinter. SQLite is required by Layman's telemetry;
these observations do not justify removing runtime dependencies.

Linux x64's Python shared library is 32,222,648 uncompressed bytes and 13,553,500
stored bytes. Read-only ELF section inspection found **26,252,412 bytes** of
`.debug*`, `.symtab` and `.strtab` sections. This is uncompressed section size,
not a prediction of ZIP reduction. PyInstaller's
[documented `--strip` option](https://pyinstaller.org/en/stable/usage.html#cmdoption-strip)
processes native symbol tables and is not recommended on Windows.

The build now enables this option only on Linux; Windows and macOS are unchanged.
No runtime module, feature or license file is excluded. Python-level error
reporting remains required; stripped native symbols reduce native crash/debug
detail, so debugging the native runtime may require the original unstripped
upstream libraries. Thirty-seven relevant packaging tests, including both Linux
architectures and non-Linux flag boundaries, and targeted lint pass. New Linux
builds, standalone smoke, inventory checks and measured package deltas are still
required before claiming this strategy works or reduces size. The previously
measured `b82380d` artifacts remain the pre-strip baseline.

### Verified Linux slimming result

Exact source `47af2d986dcfca9ded490319842111a7379293a4` passed all ten
validation jobs in [run 38057482797](https://github.com/Drippinblood333/layman/actions/runs/38057482797),
including both Linux standalone builds/smoke, three OS tests and release assembly;
publication was skipped. Downloaded only the two existing Linux platform
artifacts into ignored `build/ci-47af2d9-size`, without running them locally or
replacing an installation. The baseline is the earlier `b82380d` measurement.

| Platform | Previous executable bytes | New executable bytes | Previous expanded bytes | New expanded bytes | Expanded reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| Linux x64 | 34,454,672 | 16,785,424 | 34,590,450 | 16,921,202 | 51.08% |
| Linux arm64 | 33,166,352 | 16,248,400 | 33,302,132 | 16,384,180 | 50.80% |

Both retain 32 artifact files and the same 24 dependency names/versions as the
baseline. Executable SHA-256 values match `BUILD.json` and its digest-verified
bundle audit; runtime and standalone-component manifests match their build
digests. The embedded Python library is now 5,969,456 bytes on x64 and 5,956,840
on arm64; read-only ELF inspection confirms neither contains `.debug*`, `.symtab`
or `.strtab` sections. Dynamic export tables are not classified as removable
debug sections in this inspection. Executable hashes:

```text
linux-x64    7f8a11c9b7b51d920566a0e2d799288966becd556735b2ef3efc4ce215f268ea
linux-arm64  4eef06636946bea8b89ee6843d7ec0294352bfedc16ac336a159ead443e7a035
```

GitHub's platform transport artifacts are 16,927,202 bytes for x64
(ID `11671204056`) and 16,390,180 for arm64 (ID `11671943615`). These are not
the assembled candidate release ZIP sizes; those new ZIP sizes remain unmeasured.
These are separate hosted runs, not repeated controlled same-runner trials;
the observed package deltas must not be advertised as universal percentages.
No runtime feature/dependency was removed. Existing smoke and integrity coverage
passed, but does not prove every possible runtime workflow or restore stripped
native debugging detail. Windows/macOS size reductions, cold-start extraction
space, installed-profile footprint and token savings are not established.

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
