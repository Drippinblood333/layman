from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any


OWNERSHIP_MARKER = ".layman-owned.json"
OWNERSHIP_FORMAT = 1


def _marker_path(home: Path | None = None) -> Path:
    return (home or layman_home()) / OWNERSHIP_MARKER


def _managed_entries() -> set[str]:
    return {
        OWNERSHIP_MARKER,
        "marketplace",
        "plus-eval.jsonl",
        "plus-workspace",
        "router.log",
        "router.pid",
        "state.json",
        "usage.sqlite3",
        "usage.sqlite3-shm",
        "usage.sqlite3-wal",
    }


def mark_layman_home_owned(home: Path | None = None) -> Path:
    root = (home or layman_home()).resolve()
    created_home = not root.exists()
    root.mkdir(parents=True, exist_ok=True)
    marker = _marker_path(root)
    if not marker.exists():
        temporary = marker.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "format": OWNERSHIP_FORMAT,
                    "product": "Layman",
                    "created_home": created_home,
                    "managed_entries": sorted(_managed_entries() - {OWNERSHIP_MARKER}),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, marker)
    return marker


def purge_layman_home(home: Path | None = None) -> list[str]:
    root = (home or layman_home()).expanduser().resolve()
    marker = _marker_path(root)
    if root == Path.home().resolve() or root.parent == root:
        raise RuntimeError(f"Refusing unsafe data deletion target: {root}")
    if not marker.is_file():
        raise RuntimeError(f"Refusing to purge an unowned Layman directory (missing {OWNERSHIP_MARKER}): {root}")
    try:
        ownership = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Refusing to purge an invalid Layman ownership marker: {marker}") from exc
    if ownership.get("format") != OWNERSHIP_FORMAT or ownership.get("product") != "Layman":
        raise RuntimeError(f"Refusing to purge an unrecognized Layman ownership marker: {marker}")
    if ownership.get("created_home") is not True:
        raise RuntimeError(f"Refusing to remove a Layman home that was not created by Layman: {root}")
    managed = ownership.get("managed_entries")
    if not isinstance(managed, list) or any(
        not isinstance(name, str) or not name or Path(name).name != name for name in managed
    ):
        raise RuntimeError(f"Refusing to purge an invalid Layman managed-path manifest: {marker}")
    allowed = set(managed)
    if not allowed <= _managed_entries():
        raise RuntimeError(f"Refusing to purge an unsafe Layman managed-path manifest: {marker}")
    unexpected = sorted(path.name for path in root.iterdir() if path.name not in allowed | {OWNERSHIP_MARKER})
    if unexpected:
        raise RuntimeError(
            "Refusing to purge Layman data because unrelated entries are present: " + ", ".join(unexpected)
        )
    removed: list[str] = []
    for name in sorted(allowed):
        path = root / name
        if path.is_symlink() or path.is_file():
            path.unlink()
            removed.append(name)
        elif path.is_dir():
            shutil.rmtree(path)
            removed.append(name)
    marker.unlink()
    root.rmdir()
    return removed


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
    mark_layman_home_owned(path.parent)
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
    mark_layman_home_owned(target)
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
