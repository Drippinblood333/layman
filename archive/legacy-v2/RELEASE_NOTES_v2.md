# Layman Router v2 Release Notes

Release candidate date: 2026-07-13

Layman Router v2 adds an opt-in, loopback-only OpenAI-compatible Responses API proxy beside the existing Layman Skill v1. The v1 skill package remains byte-for-byte unchanged.

## Included

- Python 3.11+ FastAPI service with `/v1/responses`, `/v1/models`, `/healthz`, and guarded `/admin/usage/summary` endpoints.
- Rule-based task classification and configurable fast, balanced, and deep GPT-5.6 tiers.
- Explicit-model passthrough and `model="auto"` model/reasoning selection.
- Responses API field preservation, SSE forwarding, and a single pre-first-event fallback.
- SQLite usage, latency, fallback, validation, and cost telemetry without prompt or code text.
- Dry-run-first Codex user-config enable/disable commands with backup and targeted restore.
- Validated `layman-router` Codex plugin and operational Skill.
- 300 deterministic evaluation cases and an optional live auto-versus-deep runner.

## Validation completed

- 21 router unit/integration tests pass against a mock upstream.
- Static 300-case eval passes with 150 fast, 50 balanced, and 100 deep decisions.
- Codex CLI compatibility probe confirms `model="auto"`, streaming, instructions, and tools reach a custom Responses provider.
- Plugin and plugin Skill validators pass.
- Router v2 release checks pass and verify the v1 ZIP checksum.

## External validation still required

- The live 300-case auto-versus-always-deep benchmark requires a user-provided API key and incurs API charges, so it is not run automatically.
- The 20% measured-cost, validator-delta, human-score, and fallback-rate release gates must be evaluated from those live results before claiming measured savings.
- Codex Desktop should be smoke-tested after the user explicitly applies the provider configuration.

