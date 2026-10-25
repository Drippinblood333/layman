# Skip unused Git evidence during task planning

## Observed waste and change

`create_task_plan` consumes project stage and stage next steps; `run_plus_task`
consumes stage only. Both called the full inspector, including `_git_summary`.
For a Git checkout, this started `git branch --show-current` and `git status
--porcelain` even though neither result was returned or used by those callers.

Six first-failing task-plan/preview controls reproduced the unnecessary call.
The inspector now has an optional keyword-only `include_git` switch, true by
default. Only the two stage-consuming callers pass false. Skipped Git evidence
is `null`, never a synthetic clean result; normal `status`/MCP `inspect_project`
keep their full default behavior. A separate control verifies the default Git
result and identical non-Git inspection output. Original task, routing, workflow,
clarification, permissions, completion guards and returned plan fields are unchanged.

## Local verification

- Project-status, task-plan, Plus execution, MCP and CLI suites: **211 passed**.
- Scoped Ruff, whitespace and release secret scan passed.
- Existing failed-Git/unknown-status controls remain in the selected suite.
- Six mocked inspector fixtures accept the new optional keyword; no fixture
  bypasses the new negative call-count controls.

The retained private measurement is
`build/planning-git-overhead-2026-10-25/measure.py` plus `result.json`.
Script SHA-256: `21aa25677477a7a4b9325f4ac7f4af5b0fe9d63ef24a18cc02cf2edbe3431de5`.
It compares the previous unconditional Git read against the candidate on this
same checkout/input/environment, excluding only four known volatile routing
timing fields from output equality. Each entrypoint has one warm-up pair and
20 alternating-order measured pairs; no disk cache claim or subprocess output
retention. The legacy arm uses the same inspector with Git enabled, not a fake
zero-cost baseline.

| Entry point | Legacy Git processes | Candidate Git processes | Legacy median ms | Candidate median ms |
| --- | ---: | ---: | ---: | ---: |
| Plan | 2 | 0 | 105.05775 | 11.9188 |
| Dry-run preview | 2 | 0 | 113.643 | 12.2587 |

Every compared plan/preview was identical after excluding those timing fields.
These are warm in-process local measurements, not CLI cold startup, a cross-machine
latency guarantee, model-token savings or a same-quality model-task comparison.

Initially held locally for the next relevant source CI gate, rather than
triggering an all-platform build immediately after the preceding delivery.
No dependency, real model call, user config/install replacement, tag or release.

## Hosted verification and remote checkpoint

Exact source `c35c5b7a517d8bdcda65da6e744931eda05f137f` passed all ten jobs in
[validation run 40168144565](https://github.com/Drippinblood333/layman/actions/runs/40168144565),
with zero failures or active jobs. This covers three-system tests, five standalone
build/lifecycle jobs, Docker and combined asset assembly. The complete committed
diff review also caught an extra blank line at this document's EOF; this follow-up
fixes it without rebuilding source solely for a documentation whitespace change.

Fresh fetch and ancestry checking preceded a non-force main promotion attempt.
The push returned a ref-lock conflict saying main already equals this candidate
instead of the advertised `acd96e0`. It also printed a bypass warning for nine
queued required checks; this is retained as observed, not described as a clean
successful push. Independent `ls-remote` and subsequent fetch confirmed main at
this exact candidate. The conflict does not attribute the concurrent writer;
no force push or repeated promotion was used.

Main's separate [run 40168378532](https://github.com/Drippinblood333/layman/actions/runs/40168378532)
is in progress on the same SHA, not yet accepted as passed. No PR, release tag,
formal publication or replacement of the user's installed runtime occurred.
