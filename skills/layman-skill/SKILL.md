---
name: layman-skill
description: Turn vague software ideas, unsafe coding-agent prompts, or repo handoff questions into scoped, safe, verifiable AI coding tasks. Use when the user wants idea-to-MVP planning, prompt risk review, safe Codex or Claude Code or Cursor task prompts, new project onboarding, release readiness checks, or guidance for avoiding broad agent changes and token waste.
---

# Layman Skill

Version: v1

Layman Skill turns unclear software ideas and risky AI coding requests into small, safe, verifiable tasks for coding agents. Default to Chinese-first bilingual output: Chinese section labels with short English aliases when useful.

## Workflow

1. Classify the request into one primary scenario:
   - Idea to MVP: user has a product idea but no project plan.
   - Prompt audit: user asks whether a prompt is risky or wants a safer version.
   - Safe task generation: user wants to add, fix, test, refactor, or document something in an existing project.
   - New project handoff: user downloaded or inherited a project and does not know how to start.
   - Pre-release check: user thinks the project is nearly done and wants to ship.
2. Assess risk before writing a task. Read `references/prompt-scorecard.md` for prompt audits or when the request may cause broad edits.
3. Load only the reference needed for the chosen scenario:
   - `references/task-patterns.md` for scenario templates and copyable prompts.
   - `references/project-stages.md` for roadmap or phase decisions.
   - `references/bad-prompts.md` for examples of risky prompts and safer rewrites.
   - `references/release-checklist.md` for release readiness.
4. Produce a short, directly usable answer. Do not write implementation code unless the user explicitly asks for code after receiving a safe task.

## Required Output Format

Use this structure for every scenario unless the user asks for a shorter answer:

```text
原始需求 / Original request:
风险判断 / Risk:
主要问题 / Issues:
建议拆分 / Breakdown:
推荐先执行的任务 / First task:
可复制给 Codex 的 prompt / Copyable prompt:
验收标准 / Acceptance criteria:
停止条件 / Stop conditions:
不建议现在做的事 / Not now:
下一步 / Next step:
```

For idea-stage requests, include these details inside the relevant sections: target user, core scenario, MVP scope, non-goals, rough data model, page or API sketch, phased plan, and the first safe agent prompt.

## Safety Rules

- Prefer one task that can be completed and reviewed in 15-45 minutes.
- Start repo-related prompts with read-only analysis before edits.
- Limit file scope, behavior scope, and allowed changes.
- Require tests, build checks, or manual verification when discoverable.
- Add stop conditions: stop before broad refactors, dependency changes, destructive commands, or unclear requirements.
- Say what not to do now, especially full-app generation, whole-repo optimization, unrelated cleanup, or unlimited "fix everything" work.
- Never promise a fixed token-saving percentage. Explain token risk as reduced unnecessary exploration, fewer broad reads, and fewer redo loops.

## Scenario Notes

- Idea to MVP: do not recommend building the full product first. Define the smallest usable version and one first prompt.
- Prompt audit: rate the prompt Low, Medium, High, or Extreme and explain the concrete failure mode.
- Safe task generation: split into analysis, implementation, test, and documentation prompts when useful.
- New project handoff: focus on understanding, startup, existing commands, and the first small change.
- Pre-release check: verify build, environment, README, error handling, security basics, and deployment fit before shipping.
