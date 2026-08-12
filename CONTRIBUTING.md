# Contributing to Layman

Layman accepts focused fixes, compatibility improvements, evaluation cases, and documentation corrections.

1. Open an issue before proposing a new product surface.
2. Keep changes scoped; do not weaken the high-risk deep-tier safety floor or privacy defaults.
3. Install development dependencies with `python -m pip install -e "./services/layman-router[dev]"`.
4. Run `pytest`, `evals/check_router_v2.py`, `evals/check_release.py`, and `scripts/validate-public-plugin.py`.
5. State whether a claim is measured, estimated from the API price table, or observed through ChatGPT Plus.

Do not include API keys, private prompts, source code from user projects, or saved model answers in issues or pull requests.
