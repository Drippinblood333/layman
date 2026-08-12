# Layman Project Navigator 精简路线图

版本：v0.1  
日期：2026-06-18  
定位：面向 AI Coding 新手的项目落地导航器

## 1. 一句话定位

**把模糊创意变成安全、可执行、可验收的 AI 编程任务。**

Layman Project Navigator 不是普通 prompt 生成器，也不是一键生成 App 工具。它的核心价值是帮助 AI Coding 新手在把任务交给 Codex、Claude Code、Cursor 等 coding agent 之前，先完成需求澄清、MVP 拆解、风险判断、验收标准和安全 prompt 生成。

## 2. 现实问题

AI Coding 工具降低了写代码门槛，但没有自动降低项目规划、任务拆解、验收和维护门槛。

很多新手不是卡在模型能力上，而是从第一句话就把 agent 带入了高风险路径：

- “帮我优化整个项目。”
- “帮我做一个完整 App。”
- “你自己看着改。”
- “把所有问题都修好。”

这类 prompt 通常会导致：

- agent 反复读取无关文件
- 上下文和 token 快速膨胀
- 代码改动范围失控
- 结果难以验收
- 多轮返工
- demo 难以走向可发布项目

## 3. 核心思路

Layman 要解决的不是“让 AI 少说话”，而是“让用户别从错误任务开始”。

核心流程：

```text
模糊想法
-> 需求澄清
-> MVP 范围
-> 任务拆解
-> 风险判断
-> 安全 prompt
-> 验收标准
-> 停止条件
-> 下一步
```

项目本质是三种能力的组合：

1. 创意澄清器：把模糊想法转成产品需求、用户场景和 MVP 范围。
2. 项目导航器：把需求转成分阶段路线图，并告诉用户每一步该做什么。
3. Agent 任务编译器：把每一步转成适合 coding agent 执行的低风险 prompt。

## 4. 目标用户

第一优先级用户：

- 刚开始使用 Codex / Claude Code / Cursor 的新手
- 有创意但缺少工程经验的人
- 想用 AI 做独立项目、工具、网站、小程序的人
- 会一点代码但不懂项目工程化的人
- 想减少 AI coding 返工和 token 浪费的人

暂不优先服务：

- 大型企业研发团队
- 强合规行业
- 已有成熟工程平台的专业团队
- 只想一键生成完整项目且不愿理解过程的用户

## 5. MVP 场景

第一版只验证 5 个核心场景。

### 5.1 创意转 MVP 路线

输入：

```text
我想做一个给学生背单词的小程序。
```

输出：

- 目标用户
- 核心场景
- MVP 功能
- 暂不做功能
- 数据结构草案
- 页面/接口草案
- 分阶段开发计划
- 第一条可交给 Codex 的 prompt

### 5.2 模糊 prompt 体检

输入：

```text
帮我完善整个项目。
```

输出：

- 风险等级
- 主要问题
- token 浪费原因
- 安全改写版本
- 推荐先执行的只读分析任务

### 5.3 安全任务生成

输入：

```text
我想给现有项目加登录功能。
```

输出：

- 先分析 prompt
- 实现 prompt
- 测试 prompt
- 文档 prompt
- 每一步验收标准
- 每一步停止条件

### 5.4 新手项目接手

输入：

```text
我刚下载了一个项目，不知道怎么开始。
```

输出：

- 只读项目理解 prompt
- 技术栈识别 prompt
- 启动项目 prompt
- 第一个小修复任务建议

### 5.5 发布前检查

输入：

```text
项目差不多做完了，怎么发布？
```

输出：

- 构建检查
- 环境变量检查
- README 检查
- 错误处理检查
- 安全检查
- 部署平台建议
- 发布 prompt

## 6. 第一版产品形态

第一版不做完整 Web 产品，优先做开源 Skill / 模板仓库。

原因：

- 开发成本低
- 容易快速发布
- 更适合 GitHub 传播
- 方便收集真实坏 prompt
- 后续可自然扩展到 CLI、插件和 Web

建议仓库重点展示：

```text
10 bad prompts
-> 10 risk analyses
-> 10 safe rewrites
-> 10 measurable acceptance criteria
```

## 7. 推荐目录结构

```text
layman_skill/
  skills/
    layman-project-navigator/
      SKILL.md
      references/
        prompt-scorecard.md
        task-patterns.md
        project-stages.md
        bad-prompts.md
        release-checklist.md
  examples/
    bad-to-good-prompts.md
    idea-to-roadmap.md
    project-handoff.md
  evals/
    prompts.json
    expected-output-rubric.md
  PROJECT_ROADMAP.md
  TEACHER_BRIEF.md
```

## 8. 输出格式

每次生成任务时，默认使用固定结构：

```text
原始需求：
风险判断：
主要问题：
建议拆分：
推荐先执行的任务：
可复制给 Codex 的 prompt：
验收标准：
停止条件：
不建议现在做的事：
下一步：
```

固定格式的价值：

- 新手容易理解
- 可复制使用
- 可比较
- 可评测
- 后续可扩展到插件 UI

## 9. 传播定位

“项目导航器”适合解释产品，但不一定适合传播。

更适合 GitHub 和社区传播的切入点：

- 别再让 AI “优化整个项目”
- Bad prompt linter for coding agents
- Turn vague ideas into safe Codex tasks
- Stop AI agents from trashing your repo
- Save tokens before the agent starts

传播重点应放在真实坏 prompt 案例，而不是抽象方法论。

## 10. 商业化假设

开源免费版：

- prompt 体检
- 创意转 MVP
- 安全任务模板
- 发布检查清单
- 坏 prompt 案例库

潜在付费方向：

- repo-aware CLI
- prompt 风险评分
- 多 agent 格式输出
- 项目阶段看板
- 发布/维护检查
- 团队 prompt 规范
- 面向课程、训练营、小团队的模板包

短期目标不是直接收费，而是验证真实需求、积累案例和建立开源影响力。

## 11. 验证指标

第一阶段先验证以下问题：

1. 是否有人愿意安装或复制使用。
2. 是否有人提交坏 prompt 案例。
3. 是否有人要求支持某个 agent。
4. 是否有人认为它解决了真实痛点。
5. 是否能减少大范围修改和返工。
6. 是否能让新手更清楚下一步该做什么。

可观察指标：

- GitHub stars
- forks
- issues
- 模板复制次数
- 社区评论
- 用户案例
- bad prompt 数据集规模

## 12. 主要风险

1. 定位太宽，容易像普通 prompt 模板库。
2. “项目导航器”表达不够尖锐，传播力不足。
3. 用户可能不愿先规划，仍然想直接让 AI 写。
4. 官方工具可能内置类似能力。
5. 没有真实案例和 benchmark 时，很难建立信任。

应对策略：

- 第一版只做 5 个场景。
- 首页突出坏 prompt 案例。
- 不承诺固定 token 节省比例。
- 用可验收任务替代空泛 prompt。
- 尽早建立 bad prompt 数据集和评测标准。

## 13. 阶段路线

### 阶段 0：项目定义

时间：1-3 天

交付物：

- 确定项目名称和一句话定位
- 收集 10 条真实坏 prompt
- 写出 10 条安全改写结果
- 建立第一版输出格式

### 阶段 1：Skill MVP

时间：3-7 天

交付物：

- `skills/layman-project-navigator/SKILL.md`
- `references/prompt-scorecard.md`
- `references/task-patterns.md`
- `examples/bad-to-good-prompts.md`

成功标准：

- 能稳定改写 10 条坏 prompt
- 输出包含验收标准和停止条件
- 不诱导 agent 做大范围修改

### 阶段 2：案例验证

时间：1-2 周

交付物：

- 5-10 个真实小项目测试案例
- 使用前后对比
- 用户反馈
- README 示例

### 阶段 3：开源发布

时间：1 周

交付物：

- GitHub README
- 安装说明
- 示例输入输出
- 介绍文章或视频脚本

### 阶段 4：CLI / 插件探索

时间：2-4 周

候选能力：

- 扫描项目结构
- 识别技术栈
- 识别测试、lint、build 命令
- 生成 repo-aware prompt
- prompt 风险评分

## 14. 第一版不做什么

- 不做一键生成完整项目
- 不做复杂 Web 平台
- 不做账号系统
- 不做支付
- 不做自动部署
- 不做多用户协作
- 不承诺固定 token 节省比例
- 不替代开发者 review

## 15. 当前下一步

最优先行动：

1. 写 10 条真实坏 prompt。
2. 为每条坏 prompt 写风险分析。
3. 为每条坏 prompt 写安全改写版本。
4. 为每条改写任务写验收标准。
5. 创建 Skill MVP 文件结构。
6. 用 3 个真实项目想法测试输出质量。

当前最重要的不是做大功能，而是证明：

> 用户确实需要一个工具，在 coding agent 开始工作之前，把错误任务改成安全任务。

## 16. Layman Router v2 扩展

Layman v2 在保留上述 Prompt 导航能力的基础上，新增本地智能推理调度模块。Codex 可以通过 OpenAI-compatible 自定义 provider 把 `model="auto"` 请求发送到本地代理，由代理根据当前请求、工具使用、项目 YAML、质量、预算和风险选择 fast、balanced 或 deep 模型档位及推理强度。

该模块默认只监听 `127.0.0.1`，使用用户自己的 API Key，不保存 Prompt、代码、instructions 或工具参数原文。费用节省必须通过 auto 与 always-deep 的成对真实评测证明，不能把反事实价格估算宣传为已测量收益。
