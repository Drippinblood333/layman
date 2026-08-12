# Security and privacy

- The default listener is loopback-only. Admin JSON endpoints also verify the peer address and a constant-time token comparison.
- Docker sets `admin_allow_non_loopback` only inside the container because the host publishes the port on `127.0.0.1`; do not change the Compose port to a LAN-wide binding.
- The dashboard shell contains no data. Its token is kept in `sessionStorage`, never in a URL or persistent browser storage.
- Authorization is forwarded upstream but never written to SQLite or application logs.
- Telemetry stores a one-way SHA-256 prompt hash, features, route decisions, token usage, latency, cost estimates and error categories. It does not store Prompt, instructions, code, tool arguments, response text or API keys.
- Telemetry retention defaults to 90 days and old rows are pruned at startup.
- Codex configuration writes are atomic, create backups, preserve unrelated TOML and refuse to overwrite post-install user changes during disable.
- Unknown explicit models pass through, but the router marks them unpriced instead of inventing a zero-cost estimate. Savings use only complete, priced automatic requests and remain signed so regressions are visible.
- Plus evaluation never reads or copies Codex credential files. It strips API-key and custom API-endpoint environment variables before both login checks and model execution, checks `codex login status`, refuses non-ChatGPT login, passes synthetic prompts over stdin, and uses ephemeral read-only sessions. Its default JSONL omits prompt and answer text; `--store-outputs` is an explicit privacy tradeoff intended only for synthetic evaluation data.
- `$layman-auto` receives the original task through a local MCP tool and passes it to the child Codex process over stdin. It uses ephemeral sessions, ignores user model-provider overrides, strips API billing variables, and stores neither prompt nor answer text. Deterministic destructive intent is blocked before Codex starts. MCP never exposes the override; only the local CLI can accept an exact `--allow-destructive` authorization.
- `uninstall --purge-data` removes only a Layman-created home with a valid ownership marker and managed-path manifest. It refuses pre-existing directories, unknown entries, invalid markers and unresolved Codex references.
- Router process state includes an OS process-creation token. Stop refuses to signal a live PID whose identity no longer matches, preventing stale PID reuse from terminating another process.
- Project status inspection uses bounded path and Git metadata checks. It does not read or retain source, prompt, configuration, or document contents, and it never marks a project release-ready without real verification.
- API context optimization is off unless an automatic request explicitly sets `metadata.layman_context_mode="safe"`. Safe mode removes only exact older user/assistant prose duplicates of at least 200 characters and preserves current-user, system/developer, code, and tool content.
- Router control metadata (`layman_*`) is removed before an API request is forwarded. Explicit GPT-5.6 prompt caching is off by default; it requires a non-secret cache key and an API-native marker on a caller-chosen stable prefix. Layman records only the selected cache mode and breakpoint count, plus usage-provided cache read/write token counts.

Before release, scan built archives and SQLite fixtures for secret-like values and raw eval prompt content. Synthetic eval prompts and benchmark outputs are development artifacts and must not be confused with production telemetry.
