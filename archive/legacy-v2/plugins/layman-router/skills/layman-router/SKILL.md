---
name: layman-router
description: Install, configure, start, verify, recover, and explain the local Layman Router v2 service for Codex. Use when the user asks to enable model auto-routing, open the management dashboard, preview or restore Codex provider configuration, check router health, inspect cost and fallback reports, or troubleshoot the local OpenAI-compatible Responses proxy.
---

# Layman Router

Layman Router runs as a loopback-only local service. It receives Codex Responses API requests, keeps explicit models unchanged, and routes `model="auto"` through configurable fast, balanced, or deep tiers.

## Workflow

1. Locate the repository root and the `services/layman-router` package. Read `references/operations.md` for exact commands and safety boundaries.
2. Check whether the service is installed and run `layman-router doctor` before changing configuration.
3. When enabling Codex integration, always run `layman-router codex enable --dry-run` first and show the diff. Run `--apply` only after the user explicitly asks to apply it.
4. Start the service only on `127.0.0.1`. Do not expose it to a LAN or public interface.
5. Never print, store, or request the value of `OPENAI_API_KEY`. Ask the user to set it in their environment.
6. Use `layman-router report` only after `LAYMAN_ROUTER_ADMIN_TOKEN` is set. Explain that estimated savings are counterfactual; measured savings require the offline eval.
7. Use `layman-router codex disable --apply` to restore the prior provider settings. Do not hand-edit or delete the user's entire Codex config.
8. Open `http://127.0.0.1:8787/admin/` for the dashboard. Never place the admin token in a URL, command history example, or persistent browser storage.
9. If disable reports a conflict, list backups and preview `codex restore` before applying it. Preserve post-enable user changes.

## Troubleshooting

- If health fails, verify the local process, port 8787, config path, and SQLite directory.
- If Codex receives 401, verify that `OPENAI_API_KEY` exists in the environment used to launch Codex; do not ask for its value.
- If streaming stops after output begins, report the interruption. Do not replay the request because it may duplicate tool calls.
- If routing quality is disputed, inspect the non-sensitive route reason and run the eval workflow instead of saving prompts in telemetry.
