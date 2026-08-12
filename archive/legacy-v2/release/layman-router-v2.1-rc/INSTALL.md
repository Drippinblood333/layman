# Installation

Layman Router requires Python 3.11 or newer and an OpenAI API key. It uses API billing from the key; a ChatGPT subscription is not reused.

## Windows

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-router.ps1
$env:OPENAI_API_KEY = "set-this-locally"
$env:LAYMAN_ROUTER_ADMIN_TOKEN = (.\.venv\Scripts\layman-router admin-token | Select-Object -First 1)
.\.venv\Scripts\layman-router serve
```

Open `http://127.0.0.1:8787/admin/`, enter the generated admin token, and verify the status. In another terminal, preview the Codex change:

```powershell
.\.venv\Scripts\layman-router codex enable --dry-run
```

Apply only after reviewing that diff:

```powershell
.\.venv\Scripts\layman-router codex enable --apply
```

Restart Codex and use a new task so the provider configuration is reloaded.

## macOS and Linux

```bash
chmod +x scripts/install-router.sh
./scripts/install-router.sh
export OPENAI_API_KEY="set-this-locally"
export LAYMAN_ROUTER_ADMIN_TOKEN="$(./.venv/bin/layman-router admin-token 2>/dev/null)"
./.venv/bin/layman-router serve
```

Use `./.venv/bin/layman-router codex enable --dry-run` and then `--apply` after review.

## Docker

Copy secrets into the shell environment, not the YAML file. Then run `docker compose up --build` from `services/layman-router`. The published port remains bound to `127.0.0.1` on the host. Compose explicitly permits the Docker bridge peer to use admin endpoints; this is safe only while the host-side port remains loopback-bound.

## Upgrade

Stop the router, update the source, rerun the install script, run `layman-router doctor`, then restart. Database migrations are additive and happen at startup. Back up `~/.layman-router/usage.sqlite3` before a major-version upgrade.

## Offline dashboard demo

Run `layman-router demo` to start `http://127.0.0.1:8788/admin/` with a temporary token and clearly marked synthetic telemetry. It makes no API calls and deletes its temporary database when stopped.
