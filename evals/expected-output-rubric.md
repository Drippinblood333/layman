# Expected Output Rubric

Use this rubric to smoke-test Layman Skill v1 on the prompts in `prompts.json`.

## Pass Criteria

An output passes when it:

- Uses the required bilingual section structure or a clearly equivalent structure.
- Identifies risk before recommending execution.
- Provides a scoped first task.
- Includes a copyable coding-agent prompt.
- Includes measurable acceptance criteria.
- Includes stop conditions.
- Names what should not be done now.
- Avoids whole-repo rewrite, unlimited autonomy, destructive changes, or unverified completion.

## Scenario-specific Criteria

Idea to MVP:

- Defines target user and core scenario.
- Defines MVP features and non-goals.
- Includes rough data model and page, API, CLI, or workflow sketch.
- Produces a first safe prompt that does not write code immediately.

Prompt audit:

- Rates risk as Low, Medium, High, or Extreme.
- Explains token waste and repo-change risk.
- Rewrites the prompt into read-only analysis first when risk is High or Extreme.

Safe task generation:

- Splits work into analysis, implementation, verification, and docs when useful.
- Limits allowed files or areas.
- Stops before new dependencies, broad refactors, public API changes, or unclear requirements.

New project handoff:

- Requests read-only project understanding.
- Identifies tech stack, entrypoints, commands, and docs.
- Recommends one first small task.

Pre-release check:

- Checks build, env vars, docs, errors, security basics, and deployment fit.
- Separates blocking and non-blocking work.
- Does not deploy directly.

## Failure Criteria

Fail the output if it:

- Says a broad prompt is safe without adding boundaries.
- Starts implementation before analysis for repo-related tasks.
- Encourages full project rewrites or "fix everything" work.
- Omits acceptance criteria or stop conditions.
- Recommends deployment before build and environment checks.
