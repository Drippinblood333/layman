# Bad to Good Prompts

These examples show the v1 behavior expected from Layman Skill.

## Example 1

Bad prompt:

```text
帮我优化整个项目。
```

Risk:

Extreme. The goal is vague, the scope is the whole repo, no verification is defined, and the agent may waste tokens reading unrelated files.

Safer prompt:

```text
请先只读分析项目，不要修改文件。找出最多 3 个影响启动、构建或主要用户流程的问题。输出涉及文件、风险原因、建议修复顺序和验收标准。不要做性能优化、架构重构或格式化全仓库。
```

Acceptance criteria:

- Output lists no more than 3 issues.
- No files are modified.
- Each issue includes evidence and a suggested verification method.

Stop conditions:

- Stop if the issue requires broad architecture changes.
- Stop if the relevant command or project entrypoint cannot be discovered.

## Example 2

Bad prompt:

```text
你自己看着改。
```

Risk:

Extreme. The agent receives full authority without target, scope, or stop condition.

Safer prompt:

```text
请先不要修改文件。根据当前项目状态列出 3 个可选小任务，每个任务说明目标、范围、预计修改文件和验收标准。等我选择一个任务后再执行。
```

Acceptance criteria:

- Output contains 3 small tasks.
- Each task can be reviewed independently.
- No implementation starts before user selection.

## Example 3

Bad prompt:

```text
帮我做一个完整 App。
```

Risk:

High. It skips product scoping and encourages an overbuilt first version.

Safer prompt:

```text
请先不要写代码。把这个 App 想法拆成 v1 MVP：目标用户、核心场景、首版功能、暂不做功能、页面或接口草案、数据结构草案和第一阶段开发 prompt。
```

Acceptance criteria:

- Output defines v1 scope and non-goals.
- First task is small enough for one focused coding-agent session.
- No full product architecture is generated prematurely.
