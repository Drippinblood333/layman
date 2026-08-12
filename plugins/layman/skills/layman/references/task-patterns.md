# Task Patterns

Use these patterns to generate copyable coding-agent prompts. Keep the user's original intent, but add scope, verification, and stopping rules.

## 1. Idea to MVP

Use when the user has a product idea but no implementation plan.

Required output details:

- Target user.
- Core scenario.
- MVP features.
- Non-goals for v1.
- Rough data model.
- Page, screen, CLI, or API sketch.
- Phased plan.
- First safe coding-agent prompt.

Copyable prompt pattern:

```text
请先不要写代码。基于这个想法做 MVP 拆解：[idea]

请输出：
1. 目标用户和核心使用场景
2. v1 只做的功能和明确不做的功能
3. 最小数据结构草案
4. 页面、接口或命令入口草案
5. 3-5 个阶段的开发路线
6. 第一阶段可交给 Codex 执行的安全 prompt

限制：不要设计完整商业平台，不要引入复杂架构，不要生成代码。输出要能被新手直接照着执行。
```

## 2. Prompt Audit

Use when the user asks whether a prompt is good, risky, too broad, or token-wasteful.

Copyable rewrite pattern:

```text
请先只读分析当前项目，不要修改文件。

目标：[specific outcome]
范围：[files/modules/features]

请输出：
1. 需要查看的最少文件清单和原因
2. 当前实现与你发现的问题
3. 建议修改方案
4. 预计会修改的文件
5. 验收标准

停止条件：如果需要修改超过 [N] 个文件、引入新依赖、重构公共 API、删除文件，先停止并询问。
```

## 3. Safe Task Generation

Use when the user wants a feature, bugfix, refactor, test, or docs task for an existing repo.

Generate up to four staged prompts:

- Analysis prompt: read-only, discover current implementation.
- Implementation prompt: focused change, limited files.
- Test prompt: run or add relevant verification.
- Docs prompt: update README or usage notes only when behavior changes.

Implementation prompt pattern:

```text
请实现这个小任务：[task]

已知范围：[scope]
允许修改：[allowed files or areas]
不要修改：[forbidden areas]

步骤：
1. 先简要确认你将修改哪些文件。
2. 只实现与目标直接相关的最小改动。
3. 运行可用的测试、lint 或 build 命令；如果不能运行，说明原因。
4. 总结改动、验证结果和剩余风险。

停止条件：如果发现需求不清、需要大范围重构、需要新增生产依赖、或修改超过 [N] 个文件，先停止并报告。
```

## 4. New Project Handoff

Use when the user has a downloaded, inherited, or unfamiliar project.

Copyable prompt pattern:

```text
请只读分析这个项目，不要修改文件。

请按顺序输出：
1. 项目类型和主要技术栈
2. 入口文件、核心目录和配置文件
3. 包管理器、启动命令、测试命令、构建命令
4. README 或项目文档是否足够启动
5. 可能的第一步小任务，要求 15-45 分钟内可完成

限制：不要全仓库逐文件解释，不要修复问题，不要格式化代码。只给我下一步可执行建议。
```

## 5. Pre-release Check

Use when the user says the project is nearly done and asks how to ship.

Copyable prompt pattern:

```text
请做发布前只读检查，不要修改文件。

请检查：
1. 构建、测试、lint 或类型检查命令是否存在
2. 环境变量和示例配置是否完整
3. README 是否包含安装、启动、构建和部署说明
4. 关键错误处理和空状态是否明显缺失
5. 是否有敏感信息、调试输出或危险默认配置
6. 推荐部署平台和发布前必须完成的最小清单

停止条件：不要直接部署，不要改代码，不要新增依赖。只输出阻塞项、非阻塞项和下一条安全执行 prompt。
```
