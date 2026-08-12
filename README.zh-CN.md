# Layman

**用更少的无效 AI 工作，把想法变成经过验证的软件。**

Layman 是 Codex 的优化与执行层。它帮助小白理解项目做到哪一步、下一步应该做什么，也帮助开发者用最少必要的上下文、工作流、模型推理、权限和输出完成可验证结果。

![Layman 产品流程演示](docs/assets/layman-demo.gif)

## 四个入口，一个结果

| 入口 | 作用 |
|---|---|
| `$layman` | 用普通语言把想法推进到可验证结果 |
| `$layman-status` | 根据仓库证据解释项目阶段和最佳下一步 |
| `$layman-auto` | 通过 Plus 登录自动选择可靠路径并执行一次任务 |
| `$layman-router` | 安装、诊断、恢复和解释 API 自动路由 |

Layman 只组合当前任务必要的模块：上下文、工作流、模型路由、安全、工具输出和验证。发现测试或 CI 文件不等于这些检查已经通过，因此不会据此把项目误报为“可以发布”。

## Plus 与 API 模式

| 能力 | ChatGPT 登录 | OpenAI API Key |
|---|---:|---:|
| 解释项目进度 | 支持 | 支持 |
| 把想法变成最小可用目标 | 支持 | 支持 |
| 单任务自动 Codex 执行 | 支持，实验性 | 仍需 ChatGPT 登录 |
| 上下文、压缩、文件与输出预算 | 支持 | 对显式启用的 auto 请求支持 |
| Responses `model="auto"`透明路由 | 不支持 | 支持，Beta |
| 本地使用与回退面板 | 仅演示 | 支持 |

ChatGPT 订阅不等于 API 额度。Plus 任务失败时，Layman 不会自动切换到 API 计费，也不会把订阅校准结果说成实际 API 账单节省。

## 开始使用

在 Codex 中直接说人话：

```text
Use $layman to 把我的饮食记录想法做成最小可用版本。
Use $layman-status to 告诉我这个项目做到哪一步了。
Use $layman-auto to 完成下一项任务并验证结果。
```

CLI 会通过标准输入接收任务，避免进入命令历史：

```powershell
layman status
layman plan --clipboard
layman run --dry-run --clipboard
layman run --clipboard
```

安装与 API 配置见[安装文档](docs/INSTALL.md)。API 用户修改 Codex 配置前会看到差异预览和备份；`layman uninstall` 会先移除 Layman 插件与本地市场，再恢复受管配置，并默认保留本地数据与恢复备份。无法安全移除 Codex 引用时，`--purge-data` 会拒绝删除数据。

## 优化闭环

1. 理解：有限度检查仓库结构，不保存文件正文，并区分“证据”和“已经验证”。
2. 选择：只加载任务需要的工作流与上下文模块。
3. 路由：选择 Fast、Balanced 或 Deep，高风险任务不得低于 Deep。
4. 执行：使用临时 Plus 任务或兼容 Responses API 路由。
5. 验证：没有真实测试或人工检查结果，就不声称完成。
6. 汇报：只保留结果、验证、风险和一个最佳下一步。

默认不保存 Prompt、代码、工具参数、API Key 或回答正文。API 去重仅在显式设置 `metadata.layman_context_mode="safe"` 时处理旧历史里的完全相同普通文本。

### GPT-5.6 稳定前缀缓存（显式开启）

GPT-5.6 的缓存写入本身会产生费用，因此 Layman 不猜测哪些内容稳定，也不会全局开启显式缓存。对于确实重复的 API 工作负载，把共享前缀放在前面，给其最后一个 `input_text`、`input_image` 或 `input_file` 内容块加标记，并提供一个不含敏感信息的键。Layman 会在转发前移除自己的控制元数据，写入 30 分钟的显式缓存策略，并在本地面板展示缓存读取和写入量。

```json
{
  "model": "auto",
  "metadata": {
    "layman_prompt_cache": "explicit",
    "layman_prompt_cache_key": "docs-v1"
  },
  "input": [{
    "role": "user",
    "content": [
      {"type": "input_text", "text": "重复的项目说明", "prompt_cache_breakpoint": {"mode": "explicit"}},
      {"type": "input_text", "text": "当前请求"}
    ]
  }]
}
```

只有代表性基准证明前缀确实重复且净成本下降时才应开启；普通一次性任务继续使用默认隐式缓存。

## 与其他开源项目的关系

| 项目 | 主要能力 | Layman 的融合方式 |
|---|---|---|
| Caveman | 压缩最终回答 | 结果/验证/风险输出契约 |
| RTK | 压缩命令和工具输出 | 工具输出预算；未来以外部适配器集成 |
| Spec Kit | 规格驱动开发 | 最小可用目标和验收标准工作流 |
| Superpowers | 可组合开发 Skills | 按任务渐进加载 Skills |
| Claude Code Router | 模型与提供商路由 | Codex-first 的 Plus/API 路由与安全下限 |

Layman 1.0 没有直接复制这些项目的代码，而是通过原创控制层组合兼容能力，避免代码大杂烩和许可证混乱。详见[架构](docs/ARCHITECTURE.md)与[第三方说明](THIRD_PARTY_NOTICES.md)。

## 诚实的验证状态

- 本地通过 83 项单元与集成测试以及 300 案例路由矩阵。
- 36 次 Plus 校准全部完成，默认未保存回答正文。
- 30 组 Token 对照测试中，Layman 隐藏验证为 30/30，Direct 为 29/30；但 Layman 总 Token 配对中位数增加 19.54%，读取文件也更多。
- 因此 Token 优化仍为 Experimental，不宣传固定节省比例；API 路由在完成正式真实 API 基准前保持 Beta。

更多信息：[安全](docs/SECURITY.md) · [评测](docs/BENCHMARKS.md) · [Token 负面结果](docs/TOKEN_OPTIMIZATION_2026-07-16.md) · [恢复](docs/RECOVERY.md) · [发布门禁](docs/RELEASE.md)。
