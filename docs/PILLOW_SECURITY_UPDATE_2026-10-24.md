# Pillow development dependency security update

## Evidence and scope

On 2026-10-24, GitHub's open-alert API returned 41 records for
`services/layman-router/pyproject.toml`, all naming Pillow with development scope.
Five records were critical, 23 high and 13 moderate. Their current vulnerable
version ranges all include the pinned/local version 12.3.0 and exclude 13.0.0;
each lists 13.0.0 as its first patched version. This is an alert snapshot, not an
assertion that all vulnerabilities are known or that remote alerts are closed.

The maintainer's [13.0.0 release notes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html)
confirm security fixes. [PyPI release metadata](https://pypi.org/project/pillow/13.0.0/)
requires Python >=3.11, compatible with Layman's declared minimum. GitHub and the
maintainer assign different severities to some records; counts above describe
repository alerts, not a new independent severity assessment.

Pillow is an optional `dev` dependency used by `scripts/build-demo-gif.py`.
It is absent from the default runtime dependency list and hash-locked runtime
requirements. The standalone builder explicitly excludes `PIL`. These are source
boundaries, not a fresh inspection of every existing downloadable artifact.

## Change and verification

- Update only the development pin from 12.3.0 to 13.0.0; do not add a default
  dependency, change the runtime lock, or alter user-installed Layman/Codex.
- A first-failing regression rejects the vulnerable pin and ensures Pillow does
  not become a default runtime dependency. Existing exact-pin checks remain.
- A GIF smoke test runs the actual generator with an isolated output path, then
  decodes all six 1000x560 frames and checks each 5000 ms duration. It does not
  overwrite the tracked demonstration asset or claim visual pixel equivalence.
- Initial package retrieval failed with `IncompleteRead`; tests run immediately
  afterward still used 12.3.0 and were NOT accepted as upgrade verification.
  The bounded retry installed the PyPI Windows CPython 3.14 wheel successfully.
- After explicitly confirming installed Pillow 13.0.0: release-packaging suite
  **44 passed**, `pip check` and scoped Ruff passed. No model/API calls.

## Separate remaining release blocker

The previous planning source CI
[40103178651](https://github.com/Drippinblood333/layman/actions/runs/40103178651)
is terminal failure on `4ab7c725f8c5c531c98753bf6a9988ba9137574f`.
All three OS test jobs failed at the existing locked-runtime audit, before
functional tests, on certifi 2026.7.22 / PYSEC-2026-4320
(GHSA-6q48-6c7w-9gw2), fixed version 2026.10.19. Local OSV audit reproduced it;
the output lists the same ID twice, not two distinct discovered advisory IDs.
This Pillow update does not fix that separate runtime dependency issue.

Keep main at its previous verified source. Do not dismiss alerts, weaken the
audit, rerun unchanged failing source, or publish. This development-only update
stays local until the certifi batch can share one relevant hosted validation.
Cross-platform Pillow compatibility and post-main alert closure remain unverified.
