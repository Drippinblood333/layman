# Explicit read-only requests: permission consistency

## Reproduction and change

The ordinary request `解释 target.py 的代码，不要修改文件。` previously
received `workspace-write`: only high-risk classification selected read-only.
The completion guard understood the no-edit intent, but that did not restrict
execution. Six explicit Chinese/English plan cases and one constructed native
execution regression failed before the fix; eight scope/quotation controls passed.

`plus_task_plan` now recognizes a deliberately small set of explicit no-file-edit
clauses and read-only analysis/review prefixes. Such requests select read-only even
when destructive authorization is supplied. Existing high-risk and destructive
authorization floors are unchanged. This does not treat every analysis, summary,
or occurrence of "read-only" as a global restriction. Quoted examples and fenced
code are excluded; API-only / other-files-only constraints still permit the
requested edit. Explicit global no-edit wording wins over a conflicting edit
request; the executor never silently upgrades it to write access.

The existing execution path propagates that selection consistently to CLI
`--sandbox`, `default_permissions`, `CODEX_PERMISSION_PROFILE`, and Layman's own
developer guidance when that guidance can be added without overwriting user
configuration. Original task stdin is unchanged. No new configuration probe,
dependency, telemetry, model call, or retry was introduced.

## Verification and limits

- Before fix: focused regressions **7 failed, 8 passed**.
- After fix: **122 passed** across `test_plus_run.py` and `test_cli.py`.
- Scoped Ruff, Bandit, release secret scan and `git diff --check` passed.
- The execution regression uses a mocked model stream and verifies the constructed
  native command/environment; it is not a new live sandbox or model-quality test.
- Recognition is a bounded wording check, not full natural-language understanding.
  Unrecognized paraphrases still depend on the unchanged original request and
  existing risk rules. Permission profiles constrain local commands; this change
  is not a promise that every remote connector is side-effect-free.
- Zero paid or subscription model executions. No measured token benefit claimed.

The [official permission documentation](https://learn.chatgpt.com/docs/permissions#define-and-select-a-profile),
searched and fetched on 2026-10-16, distinguishes local read-only execution from
workspace write access. The fix uses the already-supported controls rather than
introducing new native flags or relaxing permissions.

Hosted coverage for this change must be recorded separately with its exact SHA.
No installed version was replaced and no release/tag was created.
