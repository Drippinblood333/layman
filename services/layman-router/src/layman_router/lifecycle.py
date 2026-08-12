from __future__ import annotations

import json
import os
import secrets
import signal
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any, Callable

from .paths import layman_home, mark_layman_home_owned, migrate_legacy_data, read_state, write_state
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


def _process_start_token(pid: int) -> str | None:
    """Return an OS-owned process creation token so a reused PID is never signalled."""

    if pid <= 0:
        return None
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            creation = wintypes.FILETIME()
            exit_time = wintypes.FILETIME()
            kernel = wintypes.FILETIME()
            user = wintypes.FILETIME()
            if not ctypes.windll.kernel32.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_time),
                ctypes.byref(kernel),
                ctypes.byref(user),
            ):
                return None
            value = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
            return f"win:{value}"
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    proc_stat = Path(f"/proc/{pid}/stat")
    if proc_stat.is_file():
        try:
            remainder = proc_stat.read_text(encoding="ascii").rsplit(")", 1)[1].split()
            return f"proc:{remainder[19]}"
        except (OSError, IndexError, UnicodeDecodeError):
            return None
    ps = shutil.which("ps")
    if not ps:
        return None
    try:
        result = subprocess.run(
            [ps, "-o", "lstart=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    started = result.stdout.strip()
    return f"ps:{started}" if result.returncode == 0 and started else None


def process_status() -> dict[str, Any]:
    path = _pid_path()
    if not path.exists():
        return {"running": False, "pid": None}
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if raw.startswith("{"):
            record = json.loads(raw)
            pid = int(record["pid"])
            expected_start = str(record["start_token"])
            legacy = False
        else:
            pid = int(raw)
            expected_start = ""
            legacy = True
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return {"running": False, "pid": None, "stale_pid_file": True}
    running = _is_running(pid)
    actual_start = _process_start_token(pid) if running else None
    verified = bool(expected_start and actual_start == expected_start)
    return {
        "running": running,
        "pid": pid,
        "identity_verified": verified,
        "legacy_pid_file": legacy,
    }


def start_router() -> dict[str, Any]:
    current = process_status()
    if current["running"]:
        if not current.get("identity_verified"):
            raise RuntimeError(
                f"PID {current.get('pid')} is alive but is not verified as the Layman instance; refusing to replace it"
            )
        return {**current, "started": False}
    home = layman_home()
    mark_layman_home_owned(home)
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
    start_token = _process_start_token(process.pid)
    if not start_token:
        try:
            _terminate_router_tree(process.pid, force=True)
        except (OSError, subprocess.SubprocessError, RuntimeError):
            process.terminate()
        raise RuntimeError("Could not verify the new Layman process identity; startup was cancelled")
    pid_path = _pid_path()
    temporary = pid_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"format": 1, "pid": process.pid, "start_token": start_token}),
        encoding="utf-8",
    )
    os.replace(temporary, pid_path)
    for _ in range(30):
        if process.poll() is not None:
            raise RuntimeError(f"Layman exited during startup. Inspect {log_path}")
        time.sleep(0.1)
    return {"running": True, "pid": process.pid, "started": True, "log": str(log_path)}


def _terminate_router_tree(pid: int, *, force: bool = False) -> None:
    """Stop only the already identity-verified router process tree."""

    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            creationflags=flags,
        )
        if result.returncode != 0 and _is_running(pid):
            raise RuntimeError(
                result.stderr.strip()
                or result.stdout.strip()
                or f"Could not stop Layman process tree {pid}"
            )
        return
    os.killpg(pid, signal.SIGKILL if force else signal.SIGTERM)


def stop_router() -> dict[str, Any]:
    current = process_status()
    pid = current.get("pid")
    if not current["running"] or not pid:
        _pid_path().unlink(missing_ok=True)
        return {"running": False, "stopped": False}
    if not current.get("identity_verified"):
        return {
            **current,
            "stopped": False,
            "refused": "PID identity could not be verified; no signal was sent",
        }
    try:
        _terminate_router_tree(int(pid))
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        return {**current, "stopped": False, "error": str(exc)}
    for _ in range(50):
        if not _is_running(int(pid)):
            break
        time.sleep(0.1)
    running = _is_running(int(pid))
    if running and os.name != "nt":
        try:
            _terminate_router_tree(int(pid), force=True)
        except (OSError, subprocess.SubprocessError, RuntimeError):
            pass
        for _ in range(10):
            if not _is_running(int(pid)):
                break
            time.sleep(0.1)
        running = _is_running(int(pid))
    if not running:
        _pid_path().unlink(missing_ok=True)
    return {"running": running, "stopped": not running, "pid": pid}


def setup_state(mode: str) -> dict[str, Any]:
    copied = migrate_legacy_data()
    state = read_state()
    state.setdefault("admin_token", secrets.token_urlsafe(32))
    state["mode"] = mode
    state["data_migration"] = [{"from": str(old), "to": str(new)} for old, new in copied]
    write_state(state)
    return state


def _ensure_configured_codex_home() -> None:
    configured = os.getenv("CODEX_HOME")
    if configured:
        Path(configured).expanduser().mkdir(parents=True, exist_ok=True)


def detect_user_mode() -> tuple[str, dict[str, Any]]:
    details: dict[str, Any] = {"openai_api_key": bool(os.getenv("OPENAI_API_KEY"))}
    _ensure_configured_codex_home()
    try:
        executable = find_codex()
        details["codex_path"] = executable
        details["codex_login"] = codex_login_status(executable)
    except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
        details["codex_login"] = {"available": False, "chatgpt_login": False, "status": str(exc)}
    if details["openai_api_key"]:
        return "api", details
    return "plus", details


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / "layman-bundle"
    packaged = Path(__file__).resolve().parent / "bundle"
    if packaged.is_dir():
        return packaged
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
    _ensure_configured_codex_home()
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


def remove_codex_plugin(
    *, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    executable = find_codex()
    remove_plugin = runner(
        [executable, "plugin", "remove", "layman@layman-local", "--json"],
        capture_output=True, text=True, timeout=30, check=False,
    )
    plugin_output = " ".join((remove_plugin.stdout, remove_plugin.stderr)).strip()
    if remove_plugin.returncode != 0 and not any(
        marker in plugin_output.lower() for marker in ("not installed", "not found")
    ):
        raise RuntimeError(plugin_output or "Codex plugin removal failed")

    remove_marketplace = runner(
        [executable, "plugin", "marketplace", "remove", "layman-local", "--json"],
        capture_output=True, text=True, timeout=30, check=False,
    )
    marketplace_output = " ".join((remove_marketplace.stdout, remove_marketplace.stderr)).strip()
    marketplace_absent = any(
        marker in marketplace_output.lower() for marker in ("not configured", "not installed", "not found")
    )
    if remove_marketplace.returncode != 0 and not marketplace_absent:
        raise RuntimeError(marketplace_output or "Codex marketplace removal failed")
    return {
        "removed": True,
        "plugin": "layman",
        "marketplace": "layman-local",
        "codex_path": executable,
    }


def open_dashboard(port: int = 8787) -> str:
    url = f"http://127.0.0.1:{port}/admin/"
    webbrowser.open(url)
    return url
