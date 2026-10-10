# Third-party notices

Layman 1.0 does not copy or vendor source code from the comparison projects below. They are credited because their public designs informed the capability boundaries described in the documentation.

| Project | Upstream | License | Layman 1.0 use |
|---|---|---|---|
| Caveman | https://github.com/JuliusBrussee/caveman | MIT | Design comparison only |
| RTK | https://github.com/rtk-ai/rtk | Apache-2.0 | Repeated-log-with-counts strategy reference; original reversible Python implementation, no Rust source or RTK binary included |
| Ponytail | https://github.com/DietrichGebert/ponytail | MIT | Design reference for task-specific reuse ordering and avoiding speculative abstractions; original compact Layman instructions, no upstream skill/hooks/source bundled |
| Spec Kit | https://github.com/github/spec-kit | MIT | Workflow comparison only |
| Superpowers | https://github.com/obra/superpowers | MIT | Skill-composition comparison only |
| Claude Code Router | https://github.com/musistudio/claude-code-router | MIT | Routing-architecture comparison only |

Ponytail design review on 2026-10-10 used upstream commit
`9b58c1ffb790c075ca32e70a89cf1d80588f4abf`, especially
`skills/ponytail/SKILL.md` and `LICENSE`. Layman's own implementation is in
`services/layman-router/src/layman_router/plus_run.py` (`_execution_contract`):
reuse ordering, no speculative abstractions, preservation of validation/error
handling/accessibility, and affected-caller checks apply only to writable
development workflows. No skill file, mode system, hook, binary or third-party
dependency is copied or installed. Upstream benchmark percentages are not Layman
results; added instruction overhead must be included in future task measurements.

Layman's exact direct and transitive runtime Python dependencies are pinned in
`services/layman-router/requirements.lock`. Every public platform ZIP also includes
`runtime-dependencies.json`, which records each installed version, SPDX license
expression, package metadata URL, upstream source URL, and the evidence used for the
license conclusion. The release `sbom.cdx.json` is generated from and checked against
that same manifest. Unknown or unsupported licenses fail the release build. All
third-party packages remain under the terms of their respective authors.

Standalone ZIPs additionally contain `standalone-components.json` plus the
`THIRD_PARTY_LICENSES/` directory. The component inventory identifies the exact
embedded CPython runtime/standard library and PyInstaller version, including the
PyInstaller bootloader exception and runtime-hook license scopes. The directory
contains the license and copyright notice files extracted from every locked Python
distribution, CPython, and PyInstaller; their SHA-256 digests are checked before a
release asset is staged.

The repository copy at `third_party/cpython/LICENSE` is the exact `LICENSE.txt`
from the official CPython 3.14.3 Windows embeddable distribution. It is kept as a
digest-pinned, platform-independent source for every standalone build, because
installed Python layouts on hosted Linux and macOS runners do not reliably retain
that complete incorporated-software notice file.

Before vendoring third-party source in a future release:

1. Pin an upstream commit.
2. Record every copied file and local modification here.
3. Retain required copyright, license, and NOTICE text.
4. Keep Apache-2.0 source under its original terms rather than relabeling it as MIT.
5. Review names and logos separately from source-code permissions.
