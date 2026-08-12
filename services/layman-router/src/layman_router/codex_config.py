from __future__ import annotations

import difflib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import tomlkit


PROVIDER_ID = "layman-router"


@dataclass
class ConfigChange:
    changed: bool
    diff: str
    config_path: Path
    backup_path: Path | None = None
    conflicts: tuple[str, ...] = ()


def codex_home() -> Path:
    return Path(os.getenv("CODEX_HOME") or Path.home() / ".codex")


def _paths(home: Path | None = None) -> tuple[Path, Path]:
    root = home or codex_home()
    return root / "config.toml", root / "layman-router-state.json"


def _render_change(before: str, after: str, path: Path) -> str:
    return "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=str(path), tofile=str(path)))


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def enable_codex(*, apply: bool, home: Path | None = None) -> ConfigChange:
    config_path, state_path = _paths(home)
    before = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    document = tomlkit.parse(before)
    providers = document.get("model_providers")
    previous_provider: Any = None
    if providers is None:
        providers = tomlkit.table()
        document["model_providers"] = providers
    elif PROVIDER_ID in providers:
        previous_provider = providers[PROVIDER_ID].unwrap()

    state = {
        "model_present": "model" in document,
        "model": document.get("model"),
        "provider_present": "model_provider" in document,
        "model_provider": document.get("model_provider"),
        "router_provider_present": previous_provider is not None,
        "router_provider": previous_provider,
        "managed_model": "auto",
        "managed_model_provider": PROVIDER_ID,
    }
    document["model"] = "auto"
    document["model_provider"] = PROVIDER_ID
    provider = tomlkit.table()
    provider["name"] = "Layman Router local proxy"
    provider["base_url"] = "http://127.0.0.1:8787/v1"
    provider["wire_api"] = "responses"
    provider["env_key"] = "OPENAI_API_KEY"
    providers[PROVIDER_ID] = provider
    after = tomlkit.dumps(document)
    diff = _render_change(before, after, config_path)
    backup: Path | None = None
    if apply and before != after:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if not state_path.exists():
            _atomic_write(state_path, json.dumps(state, indent=2, ensure_ascii=False, default=str))
        if config_path.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = config_path.with_name(f"config.toml.layman-router.{stamp}.bak")
            shutil.copy2(config_path, backup)
        _atomic_write(config_path, after)
    return ConfigChange(changed=before != after, diff=diff, config_path=config_path, backup_path=backup)


def disable_codex(*, apply: bool, home: Path | None = None) -> ConfigChange:
    config_path, state_path = _paths(home)
    if not state_path.exists():
        raise FileNotFoundError(f"Layman Router state not found: {state_path}")
    before = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    document = tomlkit.parse(before)
    state = json.loads(state_path.read_text(encoding="utf-8"))

    conflicts: list[str] = []
    for key, present_key, value_key, managed_key in (
        ("model", "model_present", "model", "managed_model"),
        ("model_provider", "provider_present", "model_provider", "managed_model_provider"),
    ):
        current = document.get(key)
        if current != state.get(managed_key):
            conflicts.append(f"{key} changed after Layman Router was enabled; left unchanged")
            continue
        if state[present_key]:
            document[key] = state[value_key]
        elif key in document:
            del document[key]
    providers = document.get("model_providers")
    if providers is not None:
        current_provider = providers.get(PROVIDER_ID)
        expected_provider = {
            "name": "Layman Router local proxy",
            "base_url": "http://127.0.0.1:8787/v1",
            "wire_api": "responses",
            "env_key": "OPENAI_API_KEY",
        }
        if current_provider is not None and current_provider.unwrap() != expected_provider:
            conflicts.append("model_providers.layman-router changed after enablement; left unchanged")
        elif state["router_provider_present"]:
            restored = tomlkit.table()
            for key, value in state["router_provider"].items():
                restored[key] = value
            providers[PROVIDER_ID] = restored
        elif PROVIDER_ID in providers:
            del providers[PROVIDER_ID]
        if not providers and "model_providers" in document:
            del document["model_providers"]
    after = tomlkit.dumps(document)
    diff = _render_change(before, after, config_path)
    backup: Path | None = None
    if apply and before != after:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = config_path.with_name(f"config.toml.layman-router-disable.{stamp}.bak")
        if config_path.exists():
            shutil.copy2(config_path, backup)
        _atomic_write(config_path, after)
        if not conflicts:
            state_path.unlink()
    return ConfigChange(changed=before != after, diff=diff, config_path=config_path, backup_path=backup, conflicts=tuple(conflicts))


def list_backups(home: Path | None = None) -> list[Path]:
    config_path, _ = _paths(home)
    return sorted(config_path.parent.glob("config.toml.layman-router*.bak"), key=lambda path: path.stat().st_mtime, reverse=True)


def restore_backup(backup: str | Path, *, apply: bool, home: Path | None = None) -> ConfigChange:
    config_path, _ = _paths(home)
    candidate = Path(backup).expanduser().resolve()
    if candidate.parent != config_path.parent.resolve() or not candidate.name.startswith("config.toml.layman-router") or candidate.suffix != ".bak":
        raise ValueError("Backup must be a Layman Router config backup in the Codex home directory")
    if not candidate.exists():
        raise FileNotFoundError(f"Backup not found: {candidate}")
    before = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    after = candidate.read_text(encoding="utf-8")
    tomlkit.parse(after)
    diff = _render_change(before, after, config_path)
    safety_backup = None
    if apply and before != after:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safety_backup = config_path.with_name(f"config.toml.layman-router-pre-restore.{stamp}.bak")
        if config_path.exists():
            shutil.copy2(config_path, safety_backup)
        _atomic_write(config_path, after)
    return ConfigChange(changed=before != after, diff=diff, config_path=config_path, backup_path=safety_backup)
