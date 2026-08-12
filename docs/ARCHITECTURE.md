# Architecture

Layman is a Codex-first, evidence-first efficiency governor and execution layer. Its unit of value is a user outcome with inspectable verification evidence, not a short answer or a cheap isolated request. Plus currently reports evidence but does not machine-certify that the evidence proves the outcome.

## Control flow

```text
user idea or task
  -> bounded project inspection
  -> task, risk, and complexity classification
  -> minimal module selection
  -> model and reasoning route
  -> ephemeral or Responses execution
  -> verification evidence
  -> plain-language outcome
```

## Modules

| Module | Responsibility | Loaded or used when |
|---|---|---|
| Project status | Infer an evidence-based stage without reading file contents | Onboarding, handoff, progress, release questions |
| Context | Search before reading, deduplicate opted-in history, guide observable file-path ceilings | Repository work |
| Workflow | Choose idea, implementation, debugging, testing, or release flow | One workflow per primary task |
| Routing | Choose fast, balanced, or deep model effort | Automatic Plus or API execution |
| Safety | Separate risk classification from destructive intent; default destructive work to blocked and high-risk work to deep/read-only | Elevated or destructive risk |
| Output | Enforce tool-output limits and guide a concise final answer; retain outcome and reported verification | Every automatic execution |
| Verification | Instruct a relevant test or bounded manual check and expose the reported evidence | Tasks that claim a changed result |

The top-level `$layman` skill is intentionally short. Detailed guidance remains in one-level references and independent skills so irrelevant instructions do not consume every task's context.

## Public surfaces

- `$layman`: beginner-friendly intent-to-result coordinator.
- `$layman-status`: read-only project-stage explanation.
- `$layman-auto`: one-task Plus execution through the local MCP server.
- `$layman-router`: API route setup and recovery guidance.
- `layman status|plan|run`: equivalent terminal surfaces.
- `/v1/responses`: compatible API path; explicit models pass through.

## Open-source capability integration

Layman 1.0 implements its control layer locally rather than copying competitor repositories. This produces similar composable capability boundaries while keeping upgrades and licenses isolated:

- Caveman-like output discipline is represented by a concise outcome target.
- RTK-like tool discipline is represented by tool-output budgets; an external adapter can be added without embedding RTK internals.
- Tool-call and process limits are enforced. File-path ceilings count paths observable in structured Codex events; batch reads can make that count a conservative lower bound, not a filesystem access-control boundary.
- Spec Kit-like specification discipline is represented by smallest-outcome and acceptance-criteria workflows.
- Superpowers-like composition is represented by progressive skill loading.
- Claude Code Router-like selection is represented by the route classifier and upward-only fallback, implemented for Codex surfaces.

Any future copied or vendored source must add its upstream commit, file mapping, license, attribution, and modifications to `THIRD_PARTY_NOTICES.md` before release.

## Trust boundaries

- Project inspection records paths and booleans, never file contents.
- Plus tasks require ChatGPT login, remove API billing variables, use stdin and ephemeral sessions, and do not retry through API billing.
- MCP never exposes the destructive authorization switch. Only an exact local CLI invocation can opt into a destructive task after human review.
- In API mode, the configured Codex provider disables its own retry layer; Layman owns the single fallback policy and records every attempt whose usage is available. Plus execution does not claim control over retries internal to the signed-in Codex provider.
- API context rewriting is off by default and preserves current, privileged, code, and tool messages.
- Telemetry records route features and usage, not prompts, code, secrets, tool arguments, or answers.
- Presence of tests or CI is not proof of success. Release readiness requires actual gates and clean installation evidence.
