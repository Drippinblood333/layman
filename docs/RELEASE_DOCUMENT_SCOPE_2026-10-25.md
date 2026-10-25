# Keep release-document tasks within their requested scope

## Reproduction and bounded fix

At the release-candidate stage, `create_task_plan` treated the words `release`
and `发布`/`发版` anywhere in the request as a release-gate request. Four
first-failing English/Chinese controls reproduced the problem for updating
release notes or checking release documentation links: the returned next steps
asked for the full release gate instead of the requested document work.

The transient workflow intent check now excludes the noun phrases `release
notes`, `release documentation`, `发布说明` and `发版说明`. This is bounded
wording recognition, not a semantic parser or authorization decision. It does
not rewrite the original task, change model routing, bypass permissions, or
remove any CI/release validation. A separate release request still counts:
four controls keep the release gate for requests such as updating notes **and
then publishing**, or checking release readiness after fixing the notes.

## Verification and limits

- Before the fix: four documentation-scope controls failed; four separate
  release-request controls passed.
- After the fix: task-plan, prompt-guidance, CLI and MCP suites passed,
  **143 tests**; scoped Ruff and `git diff --check` passed.
- No model execution, dependency addition, user-configuration/installation
  change, paid API, tag or public release.
- This removes an observed unnecessary-work recommendation. It is not a
  measured reduction in end-to-end tokens or a proof of general prompt
  understanding. Exact-source hosted verification remains pending.

The pending eval-only configuration-drift diagnostic enhancement is included in
the same candidate ancestry, not reimplemented or used to reopen a sealed trial.

