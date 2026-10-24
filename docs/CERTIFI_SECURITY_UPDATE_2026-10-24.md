# Locked certifi security update

## Why this change

The existing runtime audit failed on all three OS test jobs in
[40103178651](https://github.com/Drippinblood333/layman/actions/runs/40103178651),
source `4ab7c725f8c5c531c98753bf6a9988ba9137574f`. Local OSV audit reproduced
certifi 2026.7.22 / PYSEC-2026-4320 (same advisory ID emitted twice).

The [maintainer advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2)
identifies compromised emSign intermediates. The
[reviewed advisory](https://github.com/advisories/GHSA-6q48-6c7w-9gw2)
recommends 2026.10.19 or later: 2026.10.18 removed all emSign roots, while
2026.10.19 restored unaffected roots. This targeted repair chooses the explicit
fixed version, not a claim that it is the newest release (2026.10.23 also exists).
No application TLS verification is disabled and no system certificate store is changed.

## Bounded update

Only certifi changes in `requirements.lock`: 2026.7.22 -> 2026.10.19. Parsed
before/after dependency maps confirm every other version and package is unchanged.
The two SHA-256 hashes were obtained from
[PyPI version metadata](https://pypi.org/pypi/certifi/2026.10.19/json):

- wheel: `42d35340cc5b9ba78e818ddbff0c5b1c2b779de448a340fd1b989f5fa8670e1b`
- source: `035c1e85572b141bf1c3a3eff0e33a8eb74917522f2559075ff8d2fea780a1ae`

The project virtual environment installed the new wheel with `--require-hashes`.
Already-installed other dependencies were reused; this is not a fresh-environment
hash verification of all dependencies or a source-archive build test.

Runtime license approval and its source URL were advanced to the release commit
`662df63d7906df66f1f07c0751a3dfe9da14d914`, resolved from the annotated upstream
tag. Old/new `LICENSE` have the same Git blob SHA
`62b076cdee58ec8f34034141ba0befd9015b0c7e` and 989-byte size; MPL-2.0 unchanged.
Existing inventory/notice gates remain enabled.

## Verification and remaining gates

- New minimum-fixed-version regression failed on the old lock before the update.
- Packaging/API app/CLI/task-plan/MCP suites: **168 passed** with the new installed
  certifi. `pip check`, scoped Ruff, whitespace and release secret scan passed.
- `ssl.create_default_context(cafile=certifi.where())` successfully loaded 120
  certificates. `emSign ECC Root CA - G3` is absent. Remaining emSign common names
  are Root CA - C1, ECC Root CA - C3 and Root CA - G1. This is an offline bundle
  check, not an exploit test, full TLS interoperability test or endpoint audit.
- The post-update OSV audit and one bounded retry both failed with a
  proxy/remote-disconnect error, not an audit pass. No further identical local
  retries; use hosted validation's independent network. The existing CI audit is
  unchanged, with no advisory suppression.
- OSV warns that its `--require-hashes` option enforces hash presence rather than
  validity. The actual pip installation verifies the downloaded certifi wheel's
  hash; the OSV result must not be described as independent artifact integrity proof.

No user-installed Layman/Codex replacement, paid API, real model task or release.
Updated standalone/container builds and cross-platform validation are required
before promotion/publication. Previous candidate binaries retain their old
certificate bundles and are not retroactively repaired by this source change.
