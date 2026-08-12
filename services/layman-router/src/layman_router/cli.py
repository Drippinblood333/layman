from __future__ import annotations

import argparse
import ctypes
import http.client
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import uvicorn

from .codex_config import disable_codex, enable_codex, list_backups, restore_backup
from .config import load_config
from .lifecycle import (
    detect_user_mode,
    install_codex_plugin,
    open_dashboard,
    process_status,
    setup_state,
    start_router,
    stop_router,
)
from .paths import layman_home, read_state
from .plus_eval import DEFAULT_OUTPUT_PATH, SAFE_DEFAULT_CALL_LIMIT, codex_login_status, find_codex, run_plus_eval
from .plus_run import run_plus_task
from .project_status import inspect_project
from .task_plan import create_task_plan


def _fetch(path: str, *, admin: bool = False) -> dict:
    config = load_config()
    headers = {}
    if admin:
        token = os.getenv(config.admin_token_env) or read_state().get("admin_token")
        if not token:
            raise RuntimeError(f"Set {config.admin_token_env} before requesting reports")
        headers["X-Layman-Admin-Token"] = token
    if config.listen_host not in {"127.0.0.1", "::1", "localhost"}:
        raise RuntimeError("CLI status and report requests require a loopback listen_host")
    connection = http.client.HTTPConnection(config.listen_host, config.listen_port, timeout=5)
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        if response.status >= 400:
            raise RuntimeError(f"Router returned HTTP {response.status}")
        return json.load(response)
    finally:
        connection.close()


def _writable_ancestor(path: str) -> bool:
    candidate = Path(path).expanduser().resolve().parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate.is_dir() and os.access(candidate, os.W_OK)


def _clipboard_task() -> str:
    if os.name == "nt":
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        user32.GetClipboardData.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        if not user32.OpenClipboard(None):
            raise RuntimeError("Could not open the Windows clipboard")
        try:
            handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
            if not handle:
                raise RuntimeError("The clipboard does not contain Unicode text")
            pointer = kernel32.GlobalLock(handle)
            if not pointer:
                raise RuntimeError("Could not read the Windows clipboard")
            try:
                return ctypes.wstring_at(pointer)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()
    candidates = (["pbpaste"] if sys.platform == "darwin" else [["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"]])
    for candidate in candidates:
        command = candidate if isinstance(candidate, list) else [candidate]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        except (FileNotFoundError, subprocess.SubprocessError):
            continue
        if result.returncode == 0:
            return result.stdout
    raise RuntimeError("Clipboard access is unavailable; pass UTF-8 task text on stdin")


def _input_task(*, clipboard: bool = False) -> str:
    if clipboard:
        task = _clipboard_task()
    else:
        if sys.stdin.isatty():
            raise RuntimeError("Pass the task on stdin or use --clipboard so it does not enter shell history")
        task = sys.stdin.read().lstrip("\ufeff")
    if not task.strip():
        raise RuntimeError("Task input must not be empty")
    return task


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="layman")
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("setup", help="Set up Layman for ChatGPT Plus or OpenAI API use")
    setup.add_argument("--mode", choices=("auto", "plus", "api"), default="auto")
    setup.add_argument("--skip-plugin", action="store_true")
    setup.add_argument("--apply-codex", action="store_true", help="Apply the API-mode Codex provider after showing its diff")
    setup.add_argument("--start", action="store_true", help="Start the API router after setup")
    commands.add_parser("start", help="Start the Layman router in the background")
    commands.add_parser("stop", help="Stop the background Layman router")
    commands.add_parser("serve", help="Run the local router")
    commands.add_parser("mcp-server", help="Run the local Layman MCP server over stdio")
    status = commands.add_parser("status", help="Explain project progress and check Layman service health")
    status.add_argument("--cwd", type=Path, default=Path.cwd())
    status.add_argument("--service-only", action="store_true", help="Return only the compatibility service status")
    plan = commands.add_parser("plan", help="Plan one stdin task without executing it or storing its text")
    plan.add_argument("--cwd", type=Path, default=Path.cwd())
    plan.add_argument("--clipboard", action="store_true", help="Read Unicode task text directly from the clipboard")
    run = commands.add_parser("run", help="Automatically route and execute one stdin task through ChatGPT login")
    run.add_argument("--cwd", type=Path, default=Path.cwd())
    run.add_argument("--codex-path")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--timeout", type=int, default=1_800)
    run.add_argument("--clipboard", action="store_true", help="Read Unicode task text directly from the clipboard")
    project = commands.add_parser("project", help="Understand an existing project without reading file contents")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    project_status = project_commands.add_parser("status", help="Estimate the current project stage from repository evidence")
    project_status.add_argument("--cwd", type=Path, default=Path.cwd())
    commands.add_parser("doctor", help="Check configuration, credentials, database, and service health")
    commands.add_parser("admin-token", help="Generate a new local dashboard token")
    demo = commands.add_parser("demo", help="Run an offline dashboard with clearly marked synthetic telemetry")
    demo.add_argument("--port", type=int, default=8788)
    report = commands.add_parser("report", help="Show the local usage summary")
    report.add_argument("--project-id")
    commands.add_parser("dashboard", help="Open the local management dashboard")
    uninstall = commands.add_parser("uninstall", help="Restore Codex configuration and stop Layman")
    uninstall.add_argument("--purge-data", action="store_true", help="Also delete ~/.layman after restoration")
    codex = commands.add_parser("codex", help="Manage Codex provider configuration")
    codex_commands = codex.add_subparsers(dest="codex_command", required=True)
    for name in ("enable", "disable"):
        command = codex_commands.add_parser(name)
        mode = command.add_mutually_exclusive_group()
        mode.add_argument("--dry-run", action="store_true", default=True)
        mode.add_argument("--apply", action="store_true")
    codex_commands.add_parser("backups", help="List Layman Router Codex config backups")
    restore = codex_commands.add_parser("restore", help="Restore a selected Layman Router backup")
    restore.add_argument("backup")
    restore_mode = restore.add_mutually_exclusive_group()
    restore_mode.add_argument("--dry-run", action="store_true", default=True)
    restore_mode.add_argument("--apply", action="store_true")
    plus = commands.add_parser("codex-plus", help="Test routing through an existing ChatGPT/Codex subscription login")
    plus_commands = plus.add_subparsers(dest="plus_command", required=True)
    plus_status = plus_commands.add_parser("status", help="Check Codex CLI and ChatGPT login without making a model call")
    plus_status.add_argument("--codex-path")
    plus_run = plus_commands.add_parser("run", help="Route one stdin task through the current ChatGPT subscription login")
    plus_run.add_argument("--cwd", type=Path, default=Path.cwd())
    plus_run.add_argument("--codex-path")
    plus_run.add_argument("--dry-run", action="store_true", help="Show the selected route without making a model call")
    plus_run.add_argument("--timeout", type=int, default=1_800)
    plus_run.add_argument("--clipboard", action="store_true", help="Read Unicode task text directly from the clipboard")
    plus_eval = plus_commands.add_parser("eval", help="Preview or run a capped auto-versus-deep subscription evaluation")
    plus_eval.add_argument("--cases", type=Path)
    plus_eval.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    plus_eval.add_argument("--workspace", type=Path, default=Path.home() / ".layman" / "plus-workspace")
    plus_eval.add_argument("--codex-path")
    plus_eval.add_argument("--max-calls", type=int, default=SAFE_DEFAULT_CALL_LIMIT)
    plus_eval.add_argument("--run", action="store_true", help="Actually consume ChatGPT/Codex subscription usage")
    plus_eval.add_argument("--allow-more-calls", action="store_true", help="Permit a cap above the safe 12-call default")
    plus_eval.add_argument("--store-outputs", action="store_true", help="Opt in to saving answer text in the result JSONL")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "setup":
            detected_mode, detection = detect_user_mode()
            mode = detected_mode if args.mode == "auto" else args.mode
            if mode == "api" and not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("API mode requires OPENAI_API_KEY in the current environment")
            state = setup_state(mode)
            result: dict[str, object] = {
                "mode": mode,
                "capabilities": ["idea-to-verified-result", "project-status", "minimal-workflow-planning"] + (
                    ["automatic-api-routing"] if mode == "api" else ["automatic-plus-task-routing"]
                ),
                "detection": detection,
                "state_path": str(layman_home() / "state.json"),
                "legacy_data_copied": state.get("data_migration", []),
            }
            if not args.skip_plugin:
                result["plugin"] = install_codex_plugin()
            if mode == "api":
                change = enable_codex(apply=args.apply_codex)
                result["codex_config_diff"] = change.diff or "No configuration changes required."
                result["codex_config_applied"] = args.apply_codex
                if args.start:
                    result["router"] = start_router()
            elif args.start:
                raise RuntimeError("The HTTP router requires API mode; Plus mode uses $layman-auto without a service")
            if mode == "plus":
                try:
                    executable = find_codex()
                    result["plus_routing"] = codex_login_status(executable)
                    result["plus_routing"]["codex_path"] = executable
                except FileNotFoundError as exc:
                    result["plus_routing"] = {"available": False, "status": str(exc)}
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if args.command == "start":
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("Starting the API router requires OPENAI_API_KEY")
            print(json.dumps(start_router(), indent=2, ensure_ascii=False))
            return 0
        if args.command == "stop":
            print(json.dumps(stop_router(), indent=2, ensure_ascii=False))
            return 0
        if args.command == "serve":
            config = load_config()
            uvicorn.run("layman_router.app:create_app", factory=True, host=config.listen_host, port=config.listen_port)
            return 0
        if args.command == "mcp-server":
            from .mcp_server import serve

            return serve()
        if args.command == "status":
            status = process_status()
            try:
                status["service"] = _fetch("/healthz")
            except (OSError, RuntimeError, TimeoutError):
                status["service"] = {"status": "offline"}
            if not args.service_only:
                status = {
                    "product": "Layman",
                    "project": inspect_project(args.cwd),
                    "router": status,
                    "meaning": "Project stage is evidence-based; release readiness still requires real verification.",
                }
            print(json.dumps(status, indent=2, ensure_ascii=False))
            return 0
        if args.command == "project":
            print(json.dumps(inspect_project(args.cwd), indent=2, ensure_ascii=False))
            return 0
        if args.command == "plan":
            print(json.dumps(create_task_plan(_input_task(clipboard=args.clipboard), args.cwd), indent=2, ensure_ascii=False))
            return 0
        if args.command == "run":
            result = run_plus_task(
                _input_task(clipboard=args.clipboard),
                cwd=args.cwd,
                codex_path=args.codex_path,
                timeout_seconds=args.timeout,
                execute=not args.dry_run,
            )
            answer = result.pop("answer", "")
            if args.dry_run:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
                if answer:
                    print(answer)
            return 0 if result.get("status", "completed") == "completed" else 1
        if args.command == "doctor":
            config = load_config()
            checks = {
                "config": "ok",
                "listen_is_loopback": config.listen_host in {"127.0.0.1", "::1", "localhost"},
                "openai_api_key": "set" if os.getenv("OPENAI_API_KEY") else "missing",
                "admin_token": "set" if (os.getenv(config.admin_token_env) or read_state().get("admin_token")) else "missing",
                "database_parent_writable": _writable_ancestor(config.database_path),
            }
            try:
                checks["service"] = _fetch("/healthz").get("status", "unknown")
            except (OSError, RuntimeError, TimeoutError):
                checks["service"] = "offline"
            print(json.dumps(checks, indent=2, ensure_ascii=False))
            return 0 if checks["listen_is_loopback"] and checks["database_parent_writable"] else 1
        if args.command == "admin-token":
            print(secrets.token_urlsafe(32))
            print("Set this value as LAYMAN_ROUTER_ADMIN_TOKEN in the router process.", file=sys.stderr)
            return 0
        if args.command == "demo":
            from .demo import seed_demo
            from .telemetry import UsageStore

            with tempfile.TemporaryDirectory(prefix="layman-router-demo-") as directory:
                os.environ["LAYMAN_ROUTER_DEMO"] = "true"
                os.environ["LAYMAN_ROUTER_PORT"] = str(args.port)
                os.environ["LAYMAN_ROUTER_DATABASE_PATH"] = str(Path(directory) / "demo.sqlite3")
                token = secrets.token_urlsafe(18)
                config = load_config()
                os.environ[config.admin_token_env] = token
                store = UsageStore(config.database_path, config)
                store.initialize()
                seed_demo(store, config)
                print(f"Dashboard: http://127.0.0.1:{args.port}/admin/")
                print(f"Temporary demo token: {token}")
                print("Synthetic data is deleted when the demo process exits.")
                uvicorn.run("layman_router.app:create_app", factory=True, host="127.0.0.1", port=args.port)
            return 0
        if args.command == "report":
            query = f"?project_id={args.project_id}" if args.project_id else ""
            print(json.dumps(_fetch(f"/admin/usage/summary{query}", admin=True), indent=2, ensure_ascii=False))
            return 0
        if args.command == "dashboard":
            print(open_dashboard(load_config().listen_port))
            return 0
        if args.command == "uninstall":
            result: dict[str, object] = {"router": stop_router(), "data_retained": not args.purge_data}
            try:
                change = disable_codex(apply=True)
                result["codex_config_restored"] = not change.conflicts
                result["conflicts"] = list(change.conflicts)
            except FileNotFoundError:
                result["codex_config_restored"] = "not-managed"
            if args.purge_data:
                home = layman_home()
                if home == Path.home().resolve() or home.parent == home:
                    raise RuntimeError(f"Refusing unsafe data deletion target: {home}")
                shutil.rmtree(home, ignore_errors=True)
                result["purged"] = str(home)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if args.command == "codex":
            if args.codex_command == "backups":
                backups = list_backups()
                print("\n".join(str(path) for path in backups) if backups else "No Layman backups found.")
                return 0
            if args.codex_command == "restore":
                change = restore_backup(args.backup, apply=args.apply)
            else:
                change = enable_codex(apply=args.apply) if args.codex_command == "enable" else disable_codex(apply=args.apply)
            print(change.diff or "No configuration changes required.")
            for conflict in change.conflicts:
                print(f"warning: {conflict}", file=sys.stderr)
            if args.apply:
                print(f"Updated: {change.config_path}")
                if change.backup_path:
                    print(f"Backup: {change.backup_path}")
            else:
                print("Dry run only. Re-run with --apply to write this change.")
            return 0
        if args.command == "codex-plus":
            if args.plus_command == "status":
                executable = find_codex(args.codex_path)
                status = codex_login_status(executable)
                status["codex_path"] = executable
                status["model_calls"] = 0
                print(json.dumps(status, indent=2, ensure_ascii=False))
                return 0 if status["available"] and status["chatgpt_login"] else 1
            if args.plus_command == "run":
                result = run_plus_task(
                    _input_task(clipboard=args.clipboard),
                    cwd=args.cwd,
                    codex_path=args.codex_path,
                    timeout_seconds=args.timeout,
                    execute=not args.dry_run,
                )
                answer = result.pop("answer", "")
                if args.dry_run:
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                else:
                    print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
                    if answer:
                        print(answer)
                return 0 if result.get("status", "completed") == "completed" else 1
            result = run_plus_eval(
                cases_path=args.cases, output=args.output, workspace=args.workspace,
                codex_path=args.codex_path, execute=args.run, max_calls=args.max_calls,
                allow_more_calls=args.allow_more_calls, store_outputs=args.store_outputs,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            if not args.run:
                print("Dry run only. Add --run to consume ChatGPT/Codex subscription usage.")
            return 0
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
