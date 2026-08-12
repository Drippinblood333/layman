# Layman Router v2 Smoke Test Report

Date: 2026-07-13

## Automated results

- Router tests: 21 passed.
- Python compile check: passed.
- Static eval: 300/300 routing expectations passed.
- Static tier distribution: fast 150, balanced 50, deep 100.
- Plugin Skill validation: passed.
- Plugin manifest validation: passed.
- v2 structure/privacy/v1-checksum gate: passed.
- Existing v1 Skill validation: passed.

## Codex compatibility probe

The probe ran Codex CLI 0.144.1 with an isolated temporary `CODEX_HOME`, a fake local provider, and a non-secret probe credential. It did not modify the user's Codex configuration or call OpenAI.

Observed request properties:

- `model`: `auto`
- `stream`: `true`
- instructions present: yes
- tools present: yes
- command exit code: 0

Multi-turn `previous_response_id` preservation is covered at the proxy integration-test layer. A real Desktop multi-turn smoke test remains opt-in because enabling the provider changes user-level Codex configuration.

## Live benchmark status

Not run. It requires a real API key and 600 billable calls for the full paired 300-case comparison. Use `evals/router-v2/run_eval.py --live` only after accepting that cost.
