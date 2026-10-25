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
  understanding.

The pending eval-only configuration-drift diagnostic enhancement is included in
the same candidate ancestry, not reimplemented or used to reopen a sealed trial.

## Hosted checkpoint and remote observation

Exact candidate `c5e8ebb4795ebada5e360926af0e76fe2553e34a` passed all ten
jobs in [validation run 40166839060](https://github.com/Drippinblood333/layman/actions/runs/40166839060),
with no failures or active jobs: three-system tests, five standalone builds and
lifecycle checks, Docker and release-asset assembly. Publication is tag-guarded;
no release tag was created. A transient `gh run watch` EOF was handled by reading
the same run through the API, not restarting CI.

Fresh fetch and ancestry checking preceded a non-force main promotion attempt.
That push returned a ref-lock conflict saying main already equals this exact
candidate rather than the advertised old `8b1aa17`. A subsequent independent
`ls-remote` and fetch confirmed main at `c5e8ebb`; the conflict alone does not
identify the concurrent writer or establish which push completed it. No force
push or repeated promotion was used.

Main's separate [run 40167086229](https://github.com/Drippinblood333/layman/actions/runs/40167086229)
is observed in progress on that same SHA, not yet accepted as successful. This
closes the bounded source validation milestone, not the full project goal.

