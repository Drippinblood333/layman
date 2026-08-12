# Layman Router Operations

Run commands from the repository root after installing `services/layman-router` into a virtual environment.

```powershell
.\.venv\Scripts\python -m pip install -e ".\services\layman-router[dev]"
.\.venv\Scripts\layman status
.\.venv\Scripts\layman doctor
.\.venv\Scripts\layman codex enable --dry-run
.\.venv\Scripts\layman codex enable --apply
.\.venv\Scripts\layman report
.\.venv\Scripts\layman codex disable --apply
.\.venv\Scripts\layman codex backups
```

On macOS or Linux, replace `.\.venv\Scripts\` with `./.venv/bin/`.

Configuration writes are user-level because Codex ignores custom provider settings in project-scoped configuration. The enable command preserves unrelated TOML, creates a timestamped backup, and writes a small restore-state file. The disable command restores only the values captured before enablement.

The service must remain loopback-only. Do not place API keys, admin tokens, prompts, code, instructions, or tool arguments in project YAML or SQLite.

The management UI is `http://127.0.0.1:8787/admin/`. If configuration recovery is needed, run `codex backups`, select a timestamped file, and preview `codex restore <path> --dry-run` before `--apply`.
