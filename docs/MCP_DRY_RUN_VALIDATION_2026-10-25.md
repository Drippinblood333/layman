# Reject malformed MCP execution switches before model work

## Reproduced problem

The MCP `run` schema already declares `dry_run` as a boolean, but its runtime
handler used `bool(value)` instead of validating incoming values. A caller that
does not enforce the schema could therefore pass `null`, `0`, `[]` or `{}` and
start execution; strings such as `"false"` instead selected preview. These are
invalid requests, not permission to infer a user's intended execution choice.

Seven first-failing controls reproduced acceptance of malformed values. Two
boolean controls preserved the legitimate `true`/`false` behavior. All execution
was mocked: no accidental real-model task was used to demonstrate the defect.

## Fix and verification

The handler now requires a real boolean before calling `run_plus_task`. Omitted
`dry_run` retains the existing false default; valid booleans retain their current
meaning. Invalid values return the fixed tool error `dry_run must be a boolean`,
with no task text or diagnostic values included. The existing ValueError protocol
boundary is retained, with a documented one-line Ruff TRY004 exception rather
than broadening exception handling or disabling a lint category.

- MCP, prompt-guidance and Plus execution suites: **188 passed**.
- Two stdio controls verify safe error responses and zero executor calls for
  malformed input; cancellation, concurrency, clarification and valid execution
  controls remain covered by the selected suites.
- Scoped Ruff, whitespace checks and release secret scan passed. The initial
  lint pass flagged TRY004; the documented protocol-boundary exception resolves
  that mismatch without changing runtime behavior.
- No dependency, schema expansion, task rewriting, model call, config/installation
  replacement, paid API, tag or release.

This prevents an observed invalid-input execution path. It is not a measured
token saving: no real task comparison or quality gate was run in this batch.

## Hosted verification and delivery

Exact source `acd96e04ad68d1a4deed9c0f21858fc15c8601e8` passed all ten jobs in
[validation CI 40167540901](https://github.com/Drippinblood333/layman/actions/runs/40167540901):
three-system tests, five standalone build/lifecycle jobs, Docker and release-asset
assembly, with zero failures or active jobs. Fresh fetch/ancestry checking
preceded a non-force fast-forward of main from `c5e8ebb`; independent `ls-remote`
confirmed the exact source SHA. Main's separate
[run 40167826666](https://github.com/Drippinblood333/layman/actions/runs/40167826666)
subsequently completed successfully: ten successful jobs, no failures. The same
handle was polled, with no restart. No PR, tag or release was created.
This closes the bounded code-validation milestone, not the entire project goal.

