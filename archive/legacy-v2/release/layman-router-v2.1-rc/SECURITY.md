# Security and privacy

- The default listener is loopback-only. Admin JSON endpoints also verify the peer address and a constant-time token comparison.
- Docker sets `admin_allow_non_loopback` only inside the container because the host publishes the port on `127.0.0.1`; do not change the Compose port to a LAN-wide binding.
- The dashboard shell contains no data. Its token is kept in `sessionStorage`, never in a URL or persistent browser storage.
- Authorization is forwarded upstream but never written to SQLite or application logs.
- Telemetry stores a one-way SHA-256 prompt hash, features, route decisions, token usage, latency, cost estimates and error categories. It does not store Prompt, instructions, code, tool arguments, response text or API keys.
- Telemetry retention defaults to 90 days and old rows are pruned at startup.
- Codex configuration writes are atomic, create backups, preserve unrelated TOML and refuse to overwrite post-install user changes during disable.
- Unknown explicit models pass through, but the router does not invent a cost estimate for an unconfigured price.

Before release, scan built archives and SQLite fixtures for secret-like values and raw eval prompt content. Synthetic eval prompts and benchmark outputs are development artifacts and must not be confused with production telemetry.
