# Bad Prompts and Safer Rewrites

Use these examples to explain risk and generate safer alternatives.

## 1. "帮我优化整个项目"

Risk: Extreme. Scope is unlimited and "optimize" has no measurable finish line.

Safer rewrite:

```text
请先只读分析项目，不要修改文件。找出最多 3 个影响启动、构建或主要用户流程的问题。输出涉及文件、风险原因、建议修复顺序和验收标准。不要做性能优化、架构重构或格式化全仓库。
```

## 2. "你自己看着改"

Risk: Extreme. It gives the agent full product and engineering authority.

Safer rewrite:

```text
请先根据当前需求列出 3 个可选小任务，每个任务说明目标、范围、预计修改文件和验收标准。不要修改文件。等我选择一个任务后再执行。
```

## 3. "帮我做一个完整 App"

Risk: High. It skips MVP definition and likely causes overbuilt output.

Safer rewrite:

```text
请先不要写代码。把这个 App 想法拆成 v1 MVP：目标用户、核心场景、首版功能、暂不做功能、页面或接口草案、数据结构草案和第一阶段开发 prompt。
```

## 4. "把所有 bug 都修好"

Risk: Extreme. "All bugs" cannot be bounded or verified.

Safer rewrite:

```text
请先只读分析现有错误来源，不要修改文件。基于测试失败、构建错误或用户描述，列出最多 3 个可复现 bug，并为第一个 bug 给出最小修复方案、预计修改文件和验收标准。
```

## 5. "重构一下代码"

Risk: High. Refactor lacks target behavior and boundaries.

Safer rewrite:

```text
请只读分析 [module/file] 的可维护性问题，不要改代码。只关注重复逻辑、命名混乱或过长函数。输出一个最小重构方案，要求不改变公共 API 和用户可见行为。
```

## 6. "运行一个小时，尽可能完善"

Risk: Extreme. Time-boxed autonomy encourages unrelated changes.

Safer rewrite:

```text
请在只读模式下评估当前项目下一步最值得做的 3 个任务。每个任务必须能在 15-45 分钟内完成，并包含验收标准。不要修改文件。
```

## 7. "加登录功能"

Risk: Medium to High. Auth touches product, security, data, and UI.

Safer rewrite:

```text
请先只读分析当前项目是否已有用户模型、路由保护、会话存储和环境配置。不要修改文件。输出最小登录方案、不可忽略的安全边界、预计修改文件、测试方式和第一步实现 prompt。
```

## 8. "帮我接入支付"

Risk: High. Payment requires provider choice, secrets, callbacks, and compliance basics.

Safer rewrite:

```text
请先不要写代码。基于当前产品目标，列出接入支付前必须确认的问题、最小购买流程、需要的环境变量、后端回调风险和发布前验收标准。
```

## 9. "把界面做漂亮"

Risk: Medium. Visual quality is subjective without target screens or style.

Safer rewrite:

```text
请先只读查看当前主要页面和样式入口，不要修改文件。基于现有设计风格，提出 3 个最小 UI 改进点，每个点说明影响页面、修改范围和人工验收方式。
```

## 10. "帮我部署上线"

Risk: High. Deployment requires build, env, target platform, secrets, and rollback expectations.

Safer rewrite:

```text
请先做发布前只读检查，不要部署也不要改文件。确认构建命令、环境变量、README、敏感信息、部署平台匹配度和阻塞项。输出下一条安全部署准备 prompt。
```
