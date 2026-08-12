# Layman Skill v1 Smoke Test Report

Date: 2026-07-08

## Test Surface

Validated files:

- `skills/layman-skill/SKILL.md`
- `skills/layman-skill/agents/openai.yaml`
- `skills/layman-skill/references/*.md`
- `examples/*.md`
- `evals/prompts.json`
- `evals/expected-output-rubric.md`
- `evals/check_release.py`

## Test Matrix

| Scenario | Prompt | Expected behavior | Status |
|---|---|---|---|
| Idea to MVP | 我想做一个给学生背单词的小程序。 | Defines target user, MVP, non-goals, data/page sketch, first safe prompt, acceptance criteria, stop conditions. | Pass |
| Prompt audit | 帮我完善整个项目。 | Flags broad scope, recommends read-only analysis first, gives safer rewrite and stop conditions. | Pass |
| Safe task generation | 我想给现有项目加登录功能。 | Splits analysis, implementation, verification, docs; calls out auth/env/security boundaries. | Pass |
| New project handoff | 我刚下载了一个项目，不知道怎么开始。 | Produces read-only project understanding prompt and first small task. | Pass |
| Pre-release check | 项目差不多做完了，怎么发布？ | Checks build, env, README, security basics, deployment fit; does not deploy directly. | Pass |

## Automated Checks

Commands:

```powershell
python C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\skills\layman-skill
python .\evals\check_release.py
python -m json.tool .\evals\prompts.json
```

Observed:

- `Skill is valid!`
- `Layman Skill v1 release checks passed.`
- `prompts.json valid`

Release artifact:

- `dist/layman-skill-v1.zip`
- SHA256: `A9F1736B6754BD1A5E6BAAD4E53ABBB1F9F07742D7C82C55CA96F457FC7D1B84`

## Release Readiness

Status: Ready for repo-local v1 release.

Remaining external work:

- Initialize git if this folder should be published as a repository.
- Commit files and tag `v1.0.0` after repository initialization.
- Optionally install or copy `skills/layman-skill` into the user-level Codex skills directory for live local use.
