# Product direction — 2026-08-12

## Decision

Position Layman as an **evidence-first efficiency governor for Codex**:

> Select the lowest sufficient model and reasoning effort, bound avoidable execution waste, preserve approval boundaries, and verify the result before calling the task complete.

Layman should not compete as another generic multi-provider proxy or promise a fixed token-saving percentage. Provider routing is already a mature category: [Claude Code Router](https://github.com/musistudio/claude-code-router) supports multiple providers, transformations and scenario routing, while [RouteLLM](https://github.com/lm-sys/RouteLLM) focuses directly on learned cost/quality routing. Layman's defensible layer is the complete route-to-result control loop: scope, risk, context, attempts, tools, output, verification and release evidence.

## Current signals

1. **Use the smallest capable GPT-6 route.** OpenAI positions GPT-6 Astra for the hardest work, GPT-6.1 Sol for balanced cost and intelligence, and GPT-6 Luna for focused high-volume tasks. Layman maps those roles to deep, balanced and fast routes, while a new blinded holdout harness compares lower model/effort arms before any future route reduction is treated as calibrated. See [Using GPT-6](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra).

2. **Lean prompts and tool surfaces are a first-class optimization.** OpenAI reports directional internal coding-agent results in which leaner system prompts improved quality while reducing tokens and cost, and explicitly recommends stating instructions once and exposing only relevant tools. This supports shrinking Layman's execution contract and measuring tool-schema and repeated-prefix overhead. The published ranges are OpenAI's internal result, not a Layman claim. See [OpenAI model guidance](https://developers.openai.com/api/docs/guides/latest-model).

3. **Caching is an ROI decision, not automatic savings.** GPT-6 cache reads are discounted while cache writes have their own published rate. Layman keeps explicit caching opt-in, reports reads and writes separately, and enables it only after repeated-prefix break-even evidence. Stable instructions remain before changing content so repeated calls can reuse the same prefix. See [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching).

4. **Keep GPT-6 features behind compatibility rules.** Astra and GPT-6.1 Sol tool calling uses the Responses API, and neither accepts `none` reasoning. Layman validates those effort constraints, uses Responses for the API router, and sets low output verbosity on fast/balanced automatic routes. Mid-conversation `configuration_update` remains deferred because it conflicts with automatic compaction/truncation and requires conversation-state coordination. See [Reasoning models](https://developers.openai.com/api/docs/guides/reasoning) and [API deployment checklist](https://developers.openai.com/api/docs/guides/deployment-checklist).

5. **Workflow ecosystems are expanding.** [GitHub Spec Kit](https://github.github.io/spec-kit/) offers a cross-agent Spec → Plan → Tasks → Implement workflow, and [Superpowers](https://github.com/obra/superpowers) offers composable development skills. Layman should interoperate with their artifacts where useful, not copy their workflows into a larger always-loaded prompt.

6. **Plugins are a distribution opportunity.** OpenAI now presents plugins as a way to extend ChatGPT and Codex with skills, MCP servers and optional UI. Layman should pursue broader plugin distribution only after its local safety, packaging and hosted-CI gates are green. See [OpenAI Developers](https://developers.openai.com/).

## Product rules

- Optimize **successful outcome cost**, gross tokens, latency and retries as separate metrics.
- Never call cached-token discounts a gross-token reduction.
- Never attribute an explicit user-selected model's savings to automatic routing.
- Never turn unknown pricing or missing usage into zero cost.
- Never lower a destructive or high-risk safety floor to win a benchmark.
- Default destructive execution to blocked; require a separate, exact, local authorization.
- Treat file, tool, retry and compaction budgets as ceilings; label the current final-answer values as soft concision targets until enforcement exists.
- Keep PTC, explicit caching, multi-agent execution and maximum reasoning opt-in until representative holdouts prove a quality-adjusted benefit.

## Delivery priorities

### Public 1.0 blockers

- Close destructive-command and uninstall-purge safety gaps with adversarial tests.
- Make retry ownership and per-attempt usage accounting explicit.
- Enforce or safely stop execution budgets; support cancellation without leaving a child task running.
- Preserve executable permissions in final Unix ZIPs and prove the Docker build context contains the plugin bundle.
- Ship a traceable Python dependency/license inventory and SBOM with every standalone artifact, plus a build-component inventory and license texts for embedded CPython and PyInstaller.
- Push `main`, run hosted Windows/macOS/Linux CI, then test a release candidate with invited users.

### Post-1.0 experiments

- Tool Search for large declared tool catalogs.
- PTC for read-only filtering, joining, ranking, deduplication and validation stages.
- Long-history compaction comparisons across full-history, response-state and compacted modes.
- Cache break-even reporting by privacy-safe prefix fingerprint.
- Optional compatibility with Spec Kit artifacts without forcing a spec workflow on small tasks.

Each experiment must use a fresh holdout and report task success, required evidence, gross/cached/uncached/output tokens, tool output, calls, retries, latency and cost. A resource reduction counts only when the same acceptance criteria still pass.
