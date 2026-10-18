# Release intent filter — 2026-10-18

## Problem and bounded change

In release-candidate projects, a substring check treated future approval notes
as current release requests. It also matched English `ship` inside `ownership`
and `membership`, selecting a full release gate for ordinary changes.

The workflow selector now removes only recognized Chinese/English future-approval
phrases from its temporary intent check and matches English release keywords at
word boundaries. This uses the existing standard-library `re` dependency;
[Python's documentation](https://docs.python.org/3.11/library/re.html#regular-expression-syntax)
defines the word-boundary behavior. The original task remains untouched. A separate
explicit release/check request still selects the release gate. High-risk routing
has precedence, as before. Permissions, model selection and authorization are not
changed. No general natural-language intent or negation understanding is claimed.

## Local evidence

- Before the fix, six negative cases failed and four positive cases passed.
- After the fix, task-plan, CLI and MCP tests: **47 passed**.
- Ruff initially caught implicit string concatenation formatting; fixed locally.
- No model invocation, API expense, installation replacement, tag or release.
- Avoiding the erroneous workflow is verified; token savings are not measured.

- Ruff, Bandit, release secret scan and whitespace checks passed; the adjacent
  evaluation helpers' 16 tests also passed. A first test command used the wrong
  directory and collected no tests; the corrected test paths produced this result.

Source commit `841eaa517c2c86ce47ab1af003a83c4c50e0aaa0` is pushed to
`codex/verify-release-intent`. Exact [CI run 39119758929](https://github.com/Drippinblood333/layman/actions/runs/39119758929)
was observed queued, not passed. Main has not been advanced to this commit.
Earlier green CI cannot certify this change. Remaining product gates, including broader
same-quality token comparisons and public installation/release checks, stay open.
