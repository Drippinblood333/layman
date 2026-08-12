from __future__ import annotations

import os
import secrets
import signal
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any

from .paths import layman_home, migrate_legacy_data, read_state, write_state
from .plus_eval import codex_login_status, find_codex


def _process_command(*args: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, "-m", "layman_router.cli", *args]


def _pid_path() -> Path:
    return layman_home() / "router.pid"


def _is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == still_active
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def process_status() -> dict[str, Any]:
    path = _pid_path()
    if not path.exists():
        return {"running": False, "pid": None}
    try:
        pid = int(path.read_text(encoding="ascii").strip())
    except (ValueError, OSError):
        return {"running": False, "pid": None, "stale_pid_file": True}
    return {"running": _is_running(pid), "pid": pid}


def start_router() -> dict[str, Any]:
    current = process_status()
    if current["running"]:
        return {**current, "started": False}
    home = layman_home()
    home.mkdir(parents=True, exist_ok=True)
    state = read_state()
    environment = os.environ.copy()
    token = state.get("admin_token")
    if token and not environment.get("LAYMAN_ROUTER_ADMIN_TOKEN"):
        environment["LAYMAN_ROUTER_ADMIN_TOKEN"] = str(token)
    log_path = home / "router.log"
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with log_path.open("a", encoding="utf-8") as log:
        process = subprocess.Popen(
            _process_command("serve"), stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            env=environment, start_new_session=os.name != "nt", creationflags=creationflags,
        )
    _pid_path().write_text(str(process.pid), encoding="ascii")
    for _ in range(30):
        if process.poll() is not None:
            raise RuntimeError(f"Layman exited during startup. Inspect {log_path}")
        time.sleep(0.1)
    return {"running": True, "pid": process.pid, "started": True, "log": str(log_path)}


def stop_router() -> dict[str, Any]:
    current = process_status()
    pid = current.get("pid")
    if not current["running"] or not pid:
        _pid_path().unlink(missing_ok=True)
        return {"running": False, "stopped": False}
    os.kill(int(pid), signal.SIGTERM)
    for _ in range(50):
        if not _is_running(int(pid)):
            break
        time.sleep(0.1)
    _pid_path().unlink(missing_ok=True)
    return {"running": _is_running(int(pid)), "stopped": not _is_running(int(pid)), "pid": pid}


def setup_state(mode: str) -> dict[str, Any]:
    copied = migrate_legacy_data()
    state = read_state()
    state.setdefault("admin_token", secrets.token_urlsafe(32))
    state["mode"] = mode
    state["data_migration"] = [{"from": str(old), "to": str(new)} for old, new in copied]
    write_state(state)
    return state


def detect_user_mode() -> tuple[str, dict[str, Any]]:
    details: dict[str, Any] = {"openai_api_key": bool(os.getenv("OPENAI_API_KEY"))}
    try:
        executable = find_codex()
        details["codex_path"] = executable
        details["codex_login"] = codex_login_status(executable)
    except (FileNotFoundError, OSError) as exc:
        details["codex_login"] = {"available": False, "chatgpt_login": False, "status": str(exc)}
    if details["openai_api_key"]:
        return "api", details
    return "plus", details


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / "layman-bundle"
    return Path(__file__).resolve().parents[4]


def install_codex_plugin() -> dict[str, Any]:
    bundle = _bundle_root()
    bundle_manifest = bundle / ".agents" / "plugins" / "marketplace.json"
    bundle_plugin = bundle / "plugins" / "layman"
    if not bundle_manifest.exists() or not bundle_plugin.exists():
        raise FileNotFoundError(f"Bundled Layman plugin is incomplete: {bundle}")
    root = layman_home() / "marketplace"
    manifest = root / ".agents" / "plugins" / "marketplace.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bundle_manifest, manifest)
    shutil.copytree(bundle_plugin, root / "plugins" / "layman", dirs_exist_ok=True)
    if not manifest.exists():
        raise FileNotFoundError(f"Durable Layman marketplace was not created: {manifest}")
    executable = find_codex()
    add_marketplace = subprocess.run(
        [executable, "plugin", "marketplace", "add", str(root)], capture_output=True, text=True, check=False,
    )
    marketplace_output = " ".join((add_marketplace.stdout, add_marketplace.stderr)).strip()
    if add_marketplace.returncode != 0 and "already" not in marketplace_output.lower():
        raise RuntimeError(marketplace_output or "Codex marketplace installation failed")
    add_plugin = subprocess.run(
        [executable, "plugin", "add", "layman@layman-local", "--json"], capture_output=True, text=True, check=False,
    )
    if add_plugin.returncode != 0:
        raise RuntimeError(add_plugin.stderr.strip() or add_plugin.stdout.strip() or "Codex plugin installation failed")
    return {"installed": True, "marketplace": "layman-local", "plugin": "layman"}


def open_dashboard(port: int = 8787) -> str:
    url = f"http://127.0.0.1:{port}/admin/"
    webbrowser.open(url)
    return url
