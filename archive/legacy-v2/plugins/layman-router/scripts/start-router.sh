#!/usr/bin/env sh
set -eu
REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo "Missing .venv. Create it at $REPO_ROOT and install services/layman-router first." >&2
  exit 1
fi
exec "$PYTHON" -m layman_router.cli serve

