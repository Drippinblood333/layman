from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, TextIO

from .execution_control import CancellationToken
from .plus_run import run_plus_task
from .project_status import inspect_project
from .task_plan import create_task_plan


PROTOCOL_VERSION = "2025-06-18"


def _write(stream: TextIO, payload: dict[str, Any]) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    stream.flush()


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _tool_definitions() -> list[dict[str, Any]]:
    workspace = {
        "workspace": {"type": "string", "description": "Absolute workspace path. Defaults to the MCP process cwd."},
    }
    closed = {"type": "object", "properties": workspace, "additionalProperties": False}
    return [
        {
            "name": "run",
            "description": "Choose the minimum suitable Codex route and execute one unchanged task through the current ChatGPT login.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "minLength": 1, "description": "The user's original task, unchanged."},
                    **workspace,
                    "dry_run": {"type": "boolean", "default": False},
                },
                "required": ["task"],
                "additionalProperties": False,
            },
            "annotations": {
                "title": "Run with Layman Auto",
                "readOnlyHint": False,
                "destructiveHint": True,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        },
        {
            "name": "plan",
            "description": "Select a minimal workflow, optimization modules, safety policy, and route without executing or retaining the task.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "minLength": 1, "description": "The user's original task, unchanged."},
                    **workspace,
                },
                "required": ["task"],
                "additionalProperties": False,
            },
            "annotations": {
                "title": "Plan with Layman",
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "inspect_project",
            "description": "Explain a project's current stage from bounded repository evidence without reading or retaining file contents.",
            "inputSchema": closed,
            "annotations": {
                "title": "Understand Project Status",
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
    ]


def _call_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    cancel_token: CancellationToken | None = None,
) -> dict[str, Any]:
    workspace_value = arguments.get("workspace")
    workspace = Path(workspace_value) if isinstance(workspace_value, str) and workspace_value else Path.cwd()
    if name == "inspect_project":
        result = inspect_project(workspace)
        return {
            "content": [{"type": "text", "text": f"Project stage: {result['stage']}. See structured result for evidence."}],
            "structuredContent": result,
            "isError": False,
        }
    task = arguments.get("task")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be a non-empty string")
    if name == "plan":
        result = create_task_plan(task, workspace)
        return {
            "content": [{"type": "text", "text": f"Plan ready: {result['workflow']} via {result['route']['route_tier']}."}],
            "structuredContent": result,
            "isError": False,
        }
    if name != "run":
        raise ValueError("Unknown tool")
    result = run_plus_task(
        task,
        cwd=workspace,
        execute=not bool(arguments.get("dry_run", False)),
        cancel_token=cancel_token,
    )
    answer = result.pop("answer", "")
    if result["mode"] == "dry-run":
        text = f"Dry run: {result['route_tier']} route; execution allowed={result.get('execution_allowed', True)}."
    elif result.get("status") == "cancelled":
        text = "Layman run cancelled."
    elif result.get("status") == "budget_exceeded":
        text = "Layman stopped the run because its execution budget was exceeded."
    else:
        text = answer
    is_error = result.get("status") in {"failed", "blocked", "cancelled", "budget_exceeded"}
    return {"content": [{"type": "text", "text": text}], "structuredContent": result, "isError": is_error}


def serve(stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> int:
    write_lock = threading.Lock()
    jobs_lock = threading.Lock()
    workers_lock = threading.Lock()
    jobs: dict[str, CancellationToken] = {}
    workers: set[threading.Thread] = set()
    run_slot = threading.BoundedSemaphore(1)

    def request_key(request_id: Any) -> str:
        return json.dumps(request_id, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def write(payload: dict[str, Any]) -> None:
        with write_lock:
            _write(stdout, payload)

    def call_tool(message: dict[str, Any], token: CancellationToken, key: str) -> None:
        request_id = message.get("id")
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        name = params.get("name")
        owns_run_slot = False
        try:
            if name not in {"run", "plan", "inspect_project"}:
                write(_error(request_id, -32602, "Unknown tool"))
                return
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            if name == "run":
                owns_run_slot = run_slot.acquire(blocking=False)
                if not owns_run_slot:
                    write(_error(request_id, -32001, "Another Layman run is already active"))
                    return
            write(_result(request_id, _call_tool(str(name), arguments, cancel_token=token)))
        except (RuntimeError, ValueError, FileNotFoundError, OSError) as exc:
            write(_result(request_id, {"content": [{"type": "text", "text": str(exc)}], "isError": True}))
        finally:
            if owns_run_slot:
                run_slot.release()
            with jobs_lock:
                jobs.pop(key, None)
            with workers_lock:
                workers.discard(threading.current_thread())

    for line in stdin:
        try:
            message = json.loads(line.lstrip("\ufeff"))
        except json.JSONDecodeError:
            continue
        if not isinstance(message, dict):
            continue
        method = message.get("method")
        request_id = message.get("id")
        if method == "initialize":
            requested = (message.get("params") or {}).get("protocolVersion")
            version = requested if isinstance(requested, str) else PROTOCOL_VERSION
            write(_result(request_id, {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "layman", "version": "1.0.0"},
            }))
        elif method == "tools/list":
            write(_result(request_id, {"tools": _tool_definitions()}))
        elif method == "tools/call":
            params = message.get("params") if isinstance(message.get("params"), dict) else {}
            name = params.get("name")
            if name not in {"run", "plan", "inspect_project"}:
                write(_error(request_id, -32602, "Unknown tool"))
                continue
            if name != "run":
                try:
                    arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
                    write(_result(request_id, _call_tool(str(name), arguments)))
                except (RuntimeError, ValueError, FileNotFoundError, OSError) as exc:
                    write(_result(request_id, {
                        "content": [{"type": "text", "text": str(exc)}],
                        "isError": True,
                    }))
                continue
            if request_id is None:
                write(_error(None, -32600, "Run requests require an id"))
                continue
            token = CancellationToken()
            key = request_key(request_id)
            with jobs_lock:
                if key in jobs:
                    write(_error(request_id, -32600, "Duplicate active request id"))
                    continue
                jobs[key] = token
            worker = threading.Thread(target=call_tool, args=(message, token, key), daemon=True)
            with workers_lock:
                workers.add(worker)
            worker.start()
        elif method == "notifications/cancelled":
            params = message.get("params") if isinstance(message.get("params"), dict) else {}
            cancelled_id = params.get("requestId")
            with jobs_lock:
                token = jobs.get(request_key(cancelled_id))
            if token is not None:
                token.cancel()
        elif method == "ping":
            write(_result(request_id, {}))
        elif request_id is not None and method not in {"notifications/initialized", "notifications/cancelled"}:
            write(_error(request_id, -32601, "Method not found"))
    with jobs_lock:
        remaining_tokens = list(jobs.values())
    for token in remaining_tokens:
        token.cancel()
    shutdown_deadline = time.monotonic() + 10
    while True:
        with workers_lock:
            pending = list(workers)
        if not pending:
            break
        for worker in pending:
            remaining = shutdown_deadline - time.monotonic()
            if remaining <= 0:
                return 1
            worker.join(timeout=min(remaining, 0.2))
    return 0


def main() -> int:
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
