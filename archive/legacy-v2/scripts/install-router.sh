#!/usr/bin/env sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' || { echo "Python 3.11+ is required" >&2; exit 1; }
[ -x "$ROOT/.venv/bin/python" ] || "$PYTHON" -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/.venv/bin/python" -m pip install -e "$ROOT/services/layman-router[dev]"
"$ROOT/.venv/bin/python" -m layman_router.cli doctor
printf '\nInstalled Layman Router. Generate a dashboard token with:\n  ./.venv/bin/layman-router admin-token\n'
printf 'Then set OPENAI_API_KEY and LAYMAN_ROUTER_ADMIN_TOKEN before starting the service.\n'
