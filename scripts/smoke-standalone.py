#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"


def platform_id() -> str:
    system = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(
        platform.system(), platform.system().lower()
    )
    machine = platform.machine().lower()
    architecture = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    return f"{system}-{architecture}"


def run(command: list[str], environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, env=environment, capture_output=True, text=True, check=True)


def parse_json(result: subprocess.CompletedProcess[str], command: str) -> dict[str, object]:
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{command} did not return JSON: {result.stdout!r}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{command} returned a non-object JSON value")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a standalone Layman executable")
    parser.add_argument("--release", type=Path, default=ROOT / "release" / f"layman-v{VERSION}")
    args = parser.parse_args()
    current_platform = platform_id()
    executable_name = "layman.exe" if os.name == "nt" else "layman"
    executable = (args.release.resolve() / current_platform / executable_name).resolve()
    if not executable.is_file():
        raise SystemExit(f"standalone executable not found: {executable}")

    with tempfile.TemporaryDirectory(prefix="layman standalone 中文 空格 ") as temporary:
        smoke_root = Path(temporary)
        environment = os.environ.copy()
        environment.pop("OPENAI_API_KEY", None)
        environment["LAYMAN_HOME"] = str(smoke_root / "layman-home")
        environment["CODEX_HOME"] = str(smoke_root / "codex-home")
        environment["LAYMAN_ROUTER_DATABASE_PATH"] = str(smoke_root / "layman-home" / "usage.sqlite3")

        run([str(executable), "--help"], environment)
        setup = parse_json(
            run([str(executable), "setup", "--mode", "plus", "--skip-plugin"], environment),
            "setup",
        )
        if setup.get("mode") != "plus":
            raise RuntimeError(f"standalone setup selected an unexpected mode: {setup}")
        state_path = Path(str(setup.get("state_path", "")))
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("codex_plugin_managed") is not False:
            raise RuntimeError(f"standalone setup did not record the skipped plugin state: {state}")

        doctor = parse_json(run([str(executable), "doctor"], environment), "doctor")
        if not doctor.get("listen_is_loopback") or not doctor.get("database_parent_writable"):
            raise RuntimeError(f"standalone doctor failed: {doctor}")

        uninstall = parse_json(
            run([str(executable), "uninstall", "--purge-data"], environment),
            "uninstall",
        )
        if Path(environment["LAYMAN_HOME"]).exists():
            raise RuntimeError("standalone uninstall did not purge the isolated Layman home")
        plugin = uninstall.get("plugin")
        if not isinstance(plugin, dict) or plugin.get("status") != "skipped during setup":
            raise RuntimeError(f"standalone uninstall reported an unexpected plugin result: {uninstall}")

        print(
            json.dumps(
                {
                    "status": "passed",
                    "platform": current_platform,
                    "executable": str(executable),
                    "doctor": doctor,
                    "uninstall": uninstall,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
