# Codex product handoff — Adaptive Reasoning direction

Date: 2026-08-15

## Purpose

This document synchronizes the latest ChatGPT product discussion into the Layman repository so Codex can inspect the existing implementation against the intended product direction.

The user’s original product idea is:

> Most users should not have to understand model families or reasoning-effort levels. The system should automatically determine how much reasoning a request needs, choose an appropriate model/effort combination, reduce unnecessary latency/token use, and preserve quality on hard or high-risk tasks.

The simplest user-facing metaphor is an **automatic transmission / thinking meter** for AI.

Potential product language discussed:

- “Stop choosing models. Just ask.”
- “Your prompt knows how much thinking it needs.”
- “Automatic reasoning effort for LLMs.”

Working concept names mentioned: AutoThink, ThinkMeter, AutoEffort, ThinkGear, ReasonRouter. These are conceptual names only. **Do not rename Layman unless explicitly instructed.**

---

## What Layman already is

Layman already overlaps substantially with this idea. It is not a greenfield router.

Current repository behavior and documented architecture indicate that Layman already provides:

- Codex-first, evidence-first execution governance;
- task/risk/complexity classification;
- FAST / BALANCED / DEEP routing;
- model + reasoning-effort selection;
- high-risk deep safety floors;
- upward fallback;
- an OpenAI Responses-compatible `model="auto"` path;
- context/tool/process/output controls;
- verification/evidence reporting;
- a local dashboard for route mix, estimated cost, latency, fallback and traces;
- a 300-case deterministic routing matrix;
- direct-vs-Layman token benchmarks;
- explicit publication of negative benchmark results;
- release/security/packaging discipline.

Preserve these strengths.

---

## Product distinction: current Layman vs the proposed reasoning autopilot

### 1. Scope

Current Layman is primarily a **Codex execution governor**. It optimizes the whole route-to-result loop: scope, context, tools, reasoning, execution, verification and evidence.

The proposed product concept is narrower at the user surface but more general across AI usage:

> Automatically select the lowest sufficient reasoning budget/model for the user’s request.

Recommendation: treat adaptive reasoning as a **core subsystem and consumer-facing capability inside Layman**, not as a replacement for Layman’s governor architecture.

### 2. Current classifier is a safe deterministic baseline, not yet a learned lowest-sufficient-effort predictor

The present `classify.py` is primarily regex/keyword/rule based and uses prompt length, code presence, task type, tool count, risk terms and metadata.

The present `routing.py` maps those features into FAST/BALANCED/DEEP presets with safety floors and fallback.

That is useful and understandable, but the long-term target should be defined differently:

> Given a quality/safety threshold, predict the cheapest/fastest model + reasoning-effort arm that remains sufficient.

This is **not identical to predicting whether a prompt looks difficult**.

### 3. Model and reasoning effort are currently coupled

Current tiers bind a model and reasoning effort together.

Future internal policy should be able to represent these separately where supported:

- model;
- reasoning effort;
- max output budget;
- optional context/tool policy.

Keep FAST/BALANCED/DEEP as compatibility presets, but avoid making them the only possible decision representation.

### 4. Missing consumer-facing “ThinkMeter” layer

The current dashboard is an operator/control-room view. The user-facing concept should eventually expose a simple pre-execution decision such as:

```text
Thinking need: High
Recommended model: ...
Reasoning: Medium/High
Why: multi-step coding + elevated risk
Mode: Balanced
Confidence: heuristic / calibrated
```

Do **not** show a fake precise 0–100 score unless calibration supports it. Start with categorical buckets plus explanation/confidence.

### 5. Current 300-case router eval is policy-regression evidence, not proof of lowest sufficient effort

The deterministic matrix is valuable for regression and safety invariants, but its expected labels are policy labels. A perfect match to those labels does not prove that a lower arm would fail or that the selected arm is optimal.

Add a separate empirical evaluation layer that runs representative tasks across multiple model/effort arms and measures:

- validator/task success;
- blinded or human semantic quality;
- input/reasoning/output/cached token use;
- latency;
- estimated cost;
- retries/fallbacks;
- file/tool usage where relevant.

For each task, derive the **lowest sufficient arm** that still passes quality and safety thresholds.

### 6. Router overhead must be measured

The routing mechanism must be much cheaper/faster than the compute it saves.

Avoid an architecture where a frontier model is called merely to decide that a cheap model should answer.

Track router latency and router compute separately. Local deterministic/rule classifiers are a valid baseline; a lightweight learned classifier can be compared later.

### 7. User objective should become a first-class policy input

Proposed simple product modes:

- **Economy** — minimize expected cost subject to hard quality/safety floors.
- **Balanced** — optimize quality-adjusted latency/cost.
- **Quality** — maximize quality while still avoiding obviously wasteful compute.

No mode may lower destructive/high-risk safety floors.

---

## Recommended architecture direction

Do not rewrite the project.

A useful layered mental model is:

```text
Layman
├─ Adaptive Reasoning Core
│  ├─ feature extraction
│  ├─ model selection
│  ├─ effort selection
│  ├─ calibration/policy
│  └─ explanation/confidence
│
├─ Codex Governor
│  ├─ context budgets
│  ├─ tool/process limits
│  ├─ safety boundaries
│  ├─ retries/fallback
│  └─ verification evidence
│
└─ Surfaces
   ├─ Codex plugin / MCP
   ├─ OpenAI-compatible proxy
   ├─ CLI
   ├─ dashboard
   └─ future ThinkMeter / chat overlay
```

The governor is potentially Layman’s defensible product moat. Adaptive reasoning is the simpler product hook.

---

## Immediate audit task for Codex

Before changing code, inspect the repository and answer the following with concrete file/function references.

### A. Capability matrix

Create a table with these rows and classify each as **Complete / Partial / Missing / Not recommended now**:

1. Task-type detection
2. Risk detection
3. Complexity estimation
4. Independent model selection
5. Independent reasoning-effort selection
6. User objective mode (Economy/Balanced/Quality)
7. Router confidence/calibration
8. Router overhead measurement
9. Pre-execution explanation
10. ThinkMeter-style user surface
11. Multi-arm lowest-sufficient-effort benchmark
12. Human/blind semantic-quality evaluation
13. High-risk safety floor
14. Upward fallback
15. Privacy-safe telemetry
16. General OpenAI-compatible proxy use
17. Codex-specific execution governance
18. Real release readiness

For every row, cite the exact repository files/functions/tests that support the classification.

### B. Find product/documentation drift

Check current repository state against:

- `README.md`
- `docs/PRODUCT_DIRECTION_2026-08-12.md`
- `docs/ARCHITECTURE.md`
- `docs/BENCHMARKS.md`
- `docs/V3_RELEASE_CHECKLIST.md`
- current GitHub Actions results

Identify stale claims, contradictory status, or completed checklist items that are still marked incomplete. Do not edit them yet; report them first.

### C. Evaluate the current routing logic

Inspect at least:

- `services/layman-router/src/layman_router/classify.py`
- `services/layman-router/src/layman_router/routing.py`
- `services/layman-router/src/layman_router/default_config.yaml`
- `services/layman-router/tests/test_classify_routing.py`
- `evals/router-v2/`

Answer:

1. What exact features determine route selection today?
2. Which features are only proxies for difficulty rather than evidence of required reasoning?
3. Where can over-routing happen?
4. Where can under-routing happen?
5. Which safety invariants must never regress?
6. Can model and effort be decoupled without breaking current API compatibility?
7. What is the smallest refactor that enables that decoupling?

### D. Evaluate benchmark validity

Distinguish clearly between:

- deterministic policy regression;
- live API calibration;
- subscription-backed Codex calibration;
- direct-vs-Layman token benchmark;
- true lowest-sufficient-effort benchmark.

Do not treat the current 300/300 deterministic result as proof that the policy is cost/quality optimal.

Note the published negative token result and preserve it. Do not hide or overwrite negative evidence.

### E. Recommend only the next 3 engineering steps

After the audit, recommend exactly three next steps, prioritized by:

1. evidence value;
2. product differentiation;
3. low regression risk;
4. ability to validate quickly.

Do not begin a large rewrite. Prefer small, reviewable changes.

---

## Suggested implementation milestones after the audit

### M1 — Structured explainable decision

Expose a structured routing-decision record containing at least:

- task type;
- risk;
- complexity/important features;
- selected model;
- selected reasoning effort;
- policy reason;
- user objective;
- confidence/calibration state;
- warning when the decision is heuristic rather than empirically calibrated.

Preserve privacy: do not retain raw prompt/code by default.

### M2 — Decouple model and effort internally

Keep the public FAST/BALANCED/DEEP compatibility presets, but create an internal representation where model and reasoning effort are separable.

Add regression tests for:

- explicit-model passthrough;
- high-risk deep floor;
- agentic minimum;
- fallback direction;
- user overrides;
- current API behavior.

### M3 — Lowest-sufficient-effort pilot benchmark

Start with a small reviewed pilot, not 1,000 prompts.

For each task, execute multiple effort/model arms with identical inputs/validation. Determine the lowest arm meeting acceptance criteria. Include router overhead in the accounting.

A resource reduction only counts when acceptance criteria still pass.

### M4 — ThinkMeter prototype

Build a minimal user-facing indicator from the structured decision record.

Start with categorical output:

```text
Auto · Balanced
Reasoning need: Medium
Reason: multi-step change + repository context
Confidence: heuristic
```

Only add a numeric 0–100 meter after empirical calibration.

### M5 — Generalize after the thesis is proven

Only after routing quality is measured should Layman consider broader chat overlays/providers. Do not expand provider count merely to look feature-complete.

---

## Product guardrails

- Never claim fixed token/cost savings without a fresh representative benchmark.
- Never count cached-token discounts as gross-token reduction.
- Never optimize token use while silently reducing task success.
- Never lower high-risk/destructive safety floors for benchmark wins.
- Never call heuristic route confidence “calibrated” unless calibration exists.
- Never make an expensive LLM routing call whose overhead eliminates expected savings.
- Never retain prompts/code in telemetry by default.
- Never turn Layman into a generic multi-provider proxy before proving the adaptive-reasoning thesis.
- Preserve explicit negative benchmark results.

---

## Product-manager assessment to keep in context

The existing project is significantly further along than a simple “reasoning indicator” prototype. Its strongest assets are not just the router but the surrounding engineering: execution controls, safety floors, verification, telemetry, benchmark harnesses, packaging and release discipline.

The main gap is conceptual/evaluation precision:

> The current system selects a policy-defined tier; the target system should eventually estimate the **minimum sufficient compute** under measurable quality/safety constraints.

That shift — plus a simple ThinkMeter-style user surface — is the recommended product differentiation.

## Instruction to Codex

Treat this file as product context, not as permission to blindly implement everything. First audit current code and evidence. Preserve working behavior. If this product direction conflicts with the existing architecture or current OpenAI/Codex capabilities, report the conflict explicitly and propose the smallest evidence-driven alternative.
