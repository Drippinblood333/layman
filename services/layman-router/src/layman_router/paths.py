from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any


def layman_home() -> Path:
    return Path(os.getenv("LAYMAN_HOME") or Path.home() / ".layman").expanduser().resolve()


def legacy_home() -> Path:
    return Path.home() / ".layman-router"


def state_path() -> Path:
    return layman_home() / "state.json"


def read_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def write_state(state: dict[str, Any]) -> Path:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def migrate_legacy_data() -> list[tuple[Path, Path]]:
    """Copy known v2 user data into ~/.layman without deleting the source."""
    source = legacy_home()
    target = layman_home()
    if not source.exists():
        return []
    copied: list[tuple[Path, Path]] = []
    target.mkdir(parents=True, exist_ok=True)
    for name in ("usage.sqlite3", "plus-eval.jsonl"):
        old, new = source / name, target / name
        if old.is_file() and not new.exists():
            shutil.copy2(old, new)
            copied.append((old, new))
    old_workspace, new_workspace = source / "plus-workspace", target / "plus-workspace"
    if old_workspace.is_dir() and not new_workspace.exists():
        shutil.copytree(old_workspace, new_workspace)
        copied.append((old_workspace, new_workspace))
    return copied
