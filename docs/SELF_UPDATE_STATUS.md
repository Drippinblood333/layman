# Project update status

Updated: 2026-10-09

## Verified checkpoint

Code commit `52ce59fbaba1470ca90ff6c09ea642b2e37bca43` passed all nine jobs in [CI run 37822090216](https://github.com/Drippinblood333/layman/actions/runs/37822090216): Windows/macOS/Linux tests, five standalone build and installation lifecycle jobs, and Docker. The current suite contains 171 router tests and 41 adaptive-reasoning harness tests. Hosted checks include dependency vulnerability auditing, distribution installation, static analysis and secret scanning.

Automatic routing now uses GPT-6 Luna / GPT-6.1 Sol / GPT-6 Astra with low / medium / high reasoning respectively. Output verbosity and output caps are configured to limit unnecessary generation. These controls are implemented, but measured token savings and task-quality equivalence are not yet established.

## Continuing updates

### Request validation follow-up

The output-options audit reproduced malformed `text` values causing explicit-model crashes or silent replacement in automatic mode. The API now returns a clear HTTP 400 before contacting the upstream model. Eighteen regression cases cover five malformed shapes across automatic, configured-explicit and custom-explicit models, plus preservation of valid format and verbosity options. The updated local suite passes 189 router tests and 41 adaptive harness tests (230 total), lint and secret scanning. Hosted validation for this follow-up is pending; the green checkpoint above refers to the preceding code, not this new change.

### Local installation drift

A zero-call dry run on 2026-10-09 found the installed `layman` executable still selecting `gpt-5.6-luna`, with a 2,000-token final-answer target and a 4,000-token tool-output limit. This differs from the updated source defaults. A repository push does not replace an already installed executable or refresh the Codex plugin cache. Local installation synchronization is awaiting the owner's choice; preserve an old-installation backup, account configuration and data when performing it. The bundled `layman-auto` instructions now name the configured routes and current GPT-6 defaults rather than the old Terra/Sol presets.

An active Codex heartbeat checks this project daily at 09:00 Asia/Shanghai, subject to the local scheduler and device being available. It advances bounded, verifiable fixes and reports meaningful progress, failures or required decisions. Dependabot checks Python dependencies and GitHub Actions weekly. Neither mechanism guarantees unattended release approval or safe automatic adoption of every upstream change.

## Remaining public-release gates

- Fresh release-candidate Plus calibration and human semantic-quality scoring.
- Explicit approval before paid API calibration. No live model benchmark was executed in this update batch.
- Complete six-arm adaptive comparison: local Codex CLI 0.160.0 passes zero-call preflight for five arms but does not expose Luna `none`. A five-arm subset cannot close the six-arm gate.
- Published prerelease installer checks and 5–10 invited testers, with no unresolved P0/P1 issue.
- Owner approval before a release tag or final public release.

The full adaptive protocol reserves a counterfactual API-cost ceiling of USD 286.35 including retries and judges. This is not actual expenditure, a subscription bill, or measured savings. See the benchmark protocol for its approval and budget controls.
