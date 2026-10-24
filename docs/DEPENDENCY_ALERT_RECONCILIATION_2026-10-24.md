# Bounded reconciliation of remaining Pillow alerts

## Current evidence

Follow-up to [the verified security update](CERTIFI_SECURITY_UPDATE_2026-10-24.md).
No application, dependency, workflow, account setting or alert state was modified
during this diagnosis.

| Source checked | Observed result |
| --- | --- |
| Repository API | Default branch is `main`; security updates enabled |
| Default-branch manifest API | Git blob `e23f3e35f88c1fdacce8c3bd3886634a1b632c71` |
| Verified source manifest at `cd613c5` | Same Git blob as default-branch manifest |
| Fresh dependency-graph SBOM | Exactly one Pillow entry, canonical purl `pkg:pypi/pillow@13.0.0` |
| Open alerts API | 41 records, all require `= 12.3.0`, no fixed timestamp |
| Latest alert update among these records | `2026-10-24T06:07:13Z`, before the repair push |
| SBOM creation time observed | `2026-10-24T14:53:33Z`, after the repair push |

Alert 41 was read independently and still says open / `= 12.3.0`, matching the
list endpoint. The list contains fewer than the requested 100 records, so the
41-count is not a truncated first page. Mixed `Pillow`/`pillow` labels are preserved
in raw results, not treated as separate installed distributions. Dependency review
for the old-main/new-main comparison returned no Pillow records; this empty result
does not independently prove the version transition or absence of vulnerabilities.

## What this establishes

Wrong default branch and failure to publish the updated manifest are excluded by
the current checks. The dependency graph recognizes 13.0.0 while alert records
still describe 12.3.0. The known alert ranges were separately checked against
13.0.0 in [the Pillow update](PILLOW_SECURITY_UPDATE_2026-10-24.md).

[GitHub's dependency-graph documentation](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-graph-data)
explains default-branch manifest updates and multiple dependency-data sources.
[Its alert documentation](https://docs.github.com/en/code-security/how-tos/manage-security-alerts/manage-dependabot-alerts/view-dependabot-alerts)
distinguishes dependency fixes from dismissals. These pages do not establish a
guaranteed reconciliation deadline or diagnose this repository's internal state.
The mismatch is observed; its server-side cause is unknown. Do not relabel all
alerts false positives or claim they have closed.

## Next action and boundaries

Stop this diagnostic batch here. At the next ordinary project heartbeat, make
one compact alert-state read, without a new automation, dummy commit, manifest
churn, dependency-graph resubmission, repeated build, advisory suppression or
manual dismissal. Continue useful installation/usability/token-efficiency work
independently. Before a formal publication, reconcile or explicitly resolve the
remaining alert-state discrepancy. If it persists and GitHub support coordination
is needed, prepare this evidence for the user; do not contact support or publish
an issue on their behalf without explicit authorization for that communication.

This is not completion of the overall goal. No new real model task or savings
claim, and no user installation or system configuration was changed.
