# Layman API Router 1.0 Beta

This package provides Layman's project inspection, task planning, Plus execution, and optional local OpenAI-compatible Responses proxy. The proxy routes only `model="auto"`; explicit model identifiers pass through unchanged. The public distribution name is `layman-codex`, and both `layman` and the legacy `layman-router` console commands are installed.

The service binds to `127.0.0.1:8787` by default. It never stores prompt, code, instruction, tool-argument, API-key, or response text. Local SQLite telemetry contains routing features, usage, latency, price-table estimates and error categories.

```powershell
python -m pip install -e ".[dev]"
layman setup --mode api
layman status
layman plan --clipboard
layman run --dry-run --clipboard
layman codex enable --dry-run
layman start
```

ChatGPT Plus users do not need this proxy for `$layman` task guidance. `layman codex-plus eval` is a separate subscription calibration path and does not validate the HTTP proxy or API billing.

See the repository [installation](../../docs/INSTALL.md), [security](../../docs/SECURITY.md), [benchmarks](../../docs/BENCHMARKS.md), [recovery](../../docs/RECOVERY.md), and [release gates](../../docs/RELEASE.md).
