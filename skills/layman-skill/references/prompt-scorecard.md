# Prompt Scorecard

Use this scorecard to judge whether a coding-agent prompt is safe to run. Prefer concrete, operational feedback over abstract advice.

## Risk Levels

| Level | Meaning | Action |
|---|---|---|
| Low | Clear goal, limited scope, allowed changes, and verification are stated. | Can run after minor cleanup. |
| Medium | Goal is understandable, but scope, files, or acceptance criteria are incomplete. | Add boundaries before execution. |
| High | Broad wording may cause unnecessary exploration, large diffs, or weak verification. | Rewrite into a read-only analysis task first. |
| Extreme | The prompt delegates all decisions to the agent, asks for whole-project changes, or permits destructive work. | Do not execute. Split into staged tasks. |

## Dimensions

| Dimension | Low-risk signal | High-risk signal |
|---|---|---|
| Goal clarity | Names the expected outcome and user-visible behavior. | Uses vague verbs like optimize, improve, perfect, fix all. |
| Scope control | Names modules, files, routes, features, or a maximum change area. | Says whole project, everything, all issues, as much as possible. |
| Change permission | States what can and cannot be changed. | Lets the agent decide freely. |
| Verification | Names tests, build, screenshots, manual checks, or acceptance criteria. | Relies on the agent saying it is done. |
| Stop condition | Defines when to stop and report. | Encourages unlimited attempts or broad refactors. |
| Token risk | Reads only relevant docs or files first. | Encourages full repo scans or repeated context-heavy exploration. |
| Output shape | Requests plan, changed files, checks, and next step. | No reporting format. |

## Default Rewrite Pattern

When risk is High or Extreme, rewrite the task into this order:

1. Read-only analysis: inspect the minimum relevant files and report findings.
2. Confirm scope: list proposed files and acceptance criteria before edits.
3. Focused implementation: change only the agreed area.
4. Verification: run available checks or explain why they cannot run.
5. Stop and summarize: report changed files, risks, and next step.

## Red Flags

- "帮我优化整个项目" / "optimize the whole project"
- "你自己看着改" / "do whatever you think is best"
- "把所有问题都修好" / "fix all issues"
- "运行一个小时尽可能完善" / "work for an hour and improve as much as possible"
- "重构一下" without naming behavior, module, or acceptance criteria

## Risk Response Requirements

Every prompt audit must include:

- The risk level and the reason for that level.
- The likely token waste source.
- The likely repo damage or review risk.
- A safer copyable prompt.
- Acceptance criteria and stop conditions.
