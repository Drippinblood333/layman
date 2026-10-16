# Current Windows artifact: bounded size audit

## Artifact identity

Downloaded `layman-windows-x64`, artifact **12034227581**, from successful
[CI 38873966973](https://github.com/Drippinblood333/layman/actions/runs/38873966973),
exact source commit `d9c5bfe617b1d7b9a5d1399ee5312300460f8e42`.
GitHub artifact metadata reports **17,411,279 bytes** for the download archive.
The executable is **17,269,436 bytes** (about 16.5 MiB), SHA-256
`d45b7708e17e0a67377264a44d6796c3ca79025b4442db5b5f740e232990ded7`.

Executable identity matches BUILD.json and bundle-audit.json. All three metadata
digest links in BUILD.json also match the downloaded files. These are internal
consistency checks, not independent publisher signing or a verified archive digest.
BUILD.json does not embed the source commit; source association comes from the
GitHub run/artifact identity. `layman.exe --help` exited zero without installation.

## Content inspection

Read the embedded CArchive and PYZ table of contents with the installed
PyInstaller archive readers, without rebuilding or installing the artifact.

- CArchive: **192 entries**; PYZ: **687 module entries**.
- Plugin/marketplace bundle: **19 files**, **26,392 bytes uncompressed** and
  **14,119 bytes compressed** (about 0.082% of executable bytes).
- No second `layman_router/bundle/` data copy was found.
- No PYZ module rooted at `pytest`, `_pytest`, `PIL`, `rich`, `requests`, or
  `setuptools` was found. This is an explicit bounded check, not an audit of
  every possible development or vendored dependency.
- Plugin file set matches current committed sources. An initial strict byte
  comparison failed; seven text files differ only in Windows CRLF versus CI LF.
  After normalizing CRLF to LF, every plugin file matches. No other content
  differences were accepted.

Largest compressed archive entries:

| Entry | Compressed bytes |
| --- | ---: |
| PYZ.pyz | 5,733,337 |
| python314.dll | 2,719,317 |
| pydantic_core extension | 1,922,016 |
| libcrypto-3.dll | 1,854,357 |
| sqlite3.dll | 843,195 |

These measurements describe executable contents, not installed/extracted disk
usage, peak memory, download speed, cold-start guarantees or token consumption.
No new clean-machine install test was run: hosted standalone smoke already
passed for this SHA, while this local check only adds artifact identity,
content inspection and a help invocation.

## Decision

Do not remove working plugin resources or runtime libraries merely to force a
size-reduction claim. The inspected plugin is tiny and the checked development
stacks are already absent. No source/dependency/packaging changes were justified
by this bounded audit. Future size work needs a measured, safely removable
component, not arbitrary module exclusions.

The [automatic main CI 38874451848](https://github.com/Drippinblood333/layman/actions/runs/38874451848)
also completed SUCCESS on the same exact SHA: all ten validation jobs passed.
No model execution, paid API, installed-version replacement, release tag or
formal publication occurred. Token savings remain unproven.
