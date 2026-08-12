from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, TextIO

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
                "destructiveHint": False,
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


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    workspace_value = arguments.get("workspace")
    workspace = Path(workspace_value) if isinstance(workspace_value, str) and workspace_value else Path.cwd()
    if name == "inspect_project":
        result = inspect_project(workspace)
        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "structuredContent": result,
            "isError": False,
        }
    task = arguments.get("task")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be a non-empty string")
    if name == "plan":
        result = create_task_plan(task, workspace)
        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "structuredContent": result,
            "isError": False,
        }
    if name != "run":
        raise ValueError("Unknown tool")
    result = run_plus_task(task, cwd=workspace, execute=not bool(arguments.get("dry_run", False)))
    answer = result.pop("answer", "")
    route = json.dumps(result, ensure_ascii=False)
    text = route if result["mode"] == "dry-run" else f"{answer}\n\nLayman route metadata: {route}".strip()
    return {"content": [{"type": "text", "text": text}], "structuredContent": result, "isError": result.get("status") == "failed"}


def serve(stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> int:
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
            _write(stdout, _result(request_id, {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "layman", "version": "1.0.0"},
            }))
        elif method == "tools/list":
            _write(stdout, _result(request_id, {"tools": _tool_definitions()}))
        elif method == "tools/call":
            params = message.get("params") if isinstance(message.get("params"), dict) else {}
            name = params.get("name")
            if name not in {"run", "plan", "inspect_project"}:
                _write(stdout, _error(request_id, -32602, "Unknown tool"))
                continue
            try:
                arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
                _write(stdout, _result(request_id, _call_tool(str(name), arguments)))
            except (RuntimeError, ValueError, FileNotFoundError, OSError) as exc:
                _write(stdout, _result(request_id, {"content": [{"type": "text", "text": str(exc)}], "isError": True}))
        elif method == "ping":
            _write(stdout, _result(request_id, {}))
        elif request_id is not None and method not in {"notifications/initialized", "notifications/cancelled"}:
            _write(stdout, _error(request_id, -32601, "Method not found"))
    return 0


def main() -> int:
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
