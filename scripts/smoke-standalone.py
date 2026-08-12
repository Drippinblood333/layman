#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import subprocess
import tempfile
import time
import urllib.request
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


def run(
    command: list[str],
    environment: dict[str, str],
    *,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        env=environment,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )


def parse_json(result: subprocess.CompletedProcess[str], command: str) -> dict[str, object]:
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{command} did not return JSON: {result.stdout!r}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{command} returned a non-object JSON value")
    return value


def _start_managed_server(
    executable: Path, environment: dict[str, str]
) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [str(executable), "serve"],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=os.name != "nt",
    )


def _windows_process_path(pid: int) -> Path:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        raise OSError(f"Could not inspect standalone server process {pid}")
    try:
        size = wintypes.DWORD(32_768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        ):
            raise OSError(f"Could not resolve standalone server process {pid}")
        return Path(buffer.value).resolve()
    finally:
        kernel32.CloseHandle(handle)


def _windows_listening_pids(port: int) -> set[int]:
    result = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    pids: set[int] = set()
    for line in result.stdout.splitlines():
        columns = line.split()
        if len(columns) < 5 or columns[0].upper() != "TCP":
            continue
        local, state, pid = columns[1], columns[3].upper(), columns[4]
        if state == "LISTENING" and local.rsplit(":", 1)[-1] == str(port):
            pids.add(int(pid))
    return pids


def _stop_managed_server(
    process: subprocess.Popen[str], executable: Path, port: int
) -> None:
    if os.name == "nt":
        pids = _windows_listening_pids(port)
        if not pids:
            raise RuntimeError("Could not identify the standalone server by its listening port")
        expected = os.path.normcase(str(executable.resolve()))
        for pid in pids:
            actual = os.path.normcase(str(_windows_process_path(pid)))
            if actual != expected:
                raise RuntimeError(
                    f"Refusing to stop unexpected process {pid} listening on test port: {actual}"
                )
        for pid in pids:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    elif process.poll() is None:
        os.killpg(process.pid, 15)
    if process.poll() is None:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    elif os.name != "nt":
        process.wait(timeout=10)


def _wait_for_closed_port(port: int) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                return
        time.sleep(0.05)
    raise RuntimeError("standalone server port remained open after shutdown")


def _stop_early_server(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            process.kill()
        process.wait(timeout=10)


def smoke_http(executable: Path, environment: dict[str, str]) -> dict[str, object]:
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    server_environment = {**environment, "LAYMAN_ROUTER_PORT": str(port)}
    process = _start_managed_server(executable, server_environment)
    started = False
    try:
        deadline = time.monotonic() + 20
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise RuntimeError(
                    f"standalone server exited early: stdout={stdout!r}, stderr={stderr!r}"
                )
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/healthz", timeout=1
                ) as response:
                    health = json.loads(response.read())
                if not isinstance(health, dict) or health.get("status") != "ok":
                    raise RuntimeError(f"standalone health check was not ok: {health}")
                started = True
                return health
            except (OSError, json.JSONDecodeError, RuntimeError) as exc:
                last_error = exc
                time.sleep(0.1)
        raise RuntimeError(f"standalone health endpoint did not start: {last_error}")
    finally:
        if started:
            _stop_managed_server(process, executable, port)
        else:
            _stop_early_server(process)
        _wait_for_closed_port(port)


def smoke_mcp(
    executable: Path, environment: dict[str, str], workspace: Path
) -> dict[str, object]:
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "plan",
                "arguments": {
                    "task": "Review this test workspace without changing files.",
                    "workspace": str(workspace),
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "inspect_project",
                "arguments": {"workspace": str(workspace)},
            },
        },
    ]
    payload = "\n".join(json.dumps(request) for request in requests) + "\n"
    result = run([str(executable), "mcp-server"], environment, input_text=payload)
    responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    by_id = {
        response.get("id"): response
        for response in responses
        if isinstance(response, dict) and response.get("id") is not None
    }
    if set(by_id) != {1, 2, 3, 4} or any("error" in by_id[key] for key in by_id):
        raise RuntimeError(f"standalone MCP smoke failed: {responses}")
    tools = by_id[2]["result"].get("tools")
    if not isinstance(tools, list) or {tool.get("name") for tool in tools} != {
        "run",
        "plan",
        "inspect_project",
    }:
        raise RuntimeError(f"standalone MCP tools are incomplete: {tools}")
    for request_id in (3, 4):
        result_payload = by_id[request_id]["result"]
        if result_payload.get("isError") is not False or not isinstance(
            result_payload.get("structuredContent"), dict
        ):
            raise RuntimeError(f"standalone MCP tool failed: {result_payload}")
    return {"protocol": by_id[1]["result"]["protocolVersion"], "tools": 3}


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

        plan = parse_json(
            run(
                [str(executable), "plan", "--cwd", str(smoke_root)],
                environment,
                input_text="Review this test workspace without changing files.\n",
            ),
            "plan",
        )
        if not isinstance(plan.get("route"), dict) or not plan.get("workflow"):
            raise RuntimeError(f"standalone plan failed: {plan}")
        dry_run = parse_json(
            run(
                [str(executable), "run", "--dry-run", "--cwd", str(smoke_root)],
                environment,
                input_text="Add a small documentation note.\n",
            ),
            "run --dry-run",
        )
        if dry_run.get("mode") != "dry-run" or not dry_run.get("execution_allowed"):
            raise RuntimeError(f"standalone dry run failed: {dry_run}")
        health = smoke_http(executable, environment)
        mcp = smoke_mcp(executable, environment, smoke_root)

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
                    "plan": {
                        "workflow": plan["workflow"],
                        "route_tier": plan["route"]["route_tier"],
                    },
                    "dry_run": {
                        "route_tier": dry_run["route_tier"],
                        "execution_allowed": dry_run["execution_allowed"],
                    },
                    "health": health,
                    "mcp": mcp,
                    "uninstall": uninstall,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
