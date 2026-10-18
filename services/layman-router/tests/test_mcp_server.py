from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
import time

import pytest
from layman_router import mcp_server
from layman_router.mcp_server import serve


def test_mcp_missing_workspace_execution_is_not_success(monkeypatch, tmp_path):
    monkeypatch.setattr(mcp_server, "run_plus_task", lambda *a, **k: {
        "mode": "run", "status": "needs_verification",
        "error_category": "workspace_execution_not_observed",
        "answer": "未观察到指定文件的工具操作，不能确认任务已完成；未自动重试。",
    })
    result = mcp_server._call_tool("run", {"task": "修复 src/a.py", "workspace": str(tmp_path)})
    assert result["isError"] is True
    assert result["structuredContent"]["status"] == "needs_verification"
    assert "不能确认任务已完成" in result["content"][0]["text"]


def test_mcp_lists_layman_run_tool():
    incoming = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        + "\n"
    )
    outgoing = io.StringIO()
    assert serve(incoming, outgoing) == 0
    messages = [json.loads(line) for line in outgoing.getvalue().splitlines()]
    assert messages[0]["result"]["serverInfo"]["name"] == "layman"
    tools = messages[1]["result"]["tools"]
    assert [tool["name"] for tool in tools] == ["run", "plan", "inspect_project"]
    tool = tools[0]
    assert tool["name"] == "run"
    assert tool["inputSchema"]["required"] == ["task"]
    assert tool["annotations"]["openWorldHint"] is False
    assert tool["annotations"]["destructiveHint"] is True
    assert "allow_destructive" not in tool["inputSchema"]["properties"]


def test_mcp_inspects_project_without_task_text(tmp_path):
    incoming = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "inspect_project", "arguments": {"workspace": str(tmp_path)},
        }}) + "\n"
    )
    outgoing = io.StringIO()
    assert serve(incoming, outgoing) == 0
    message = json.loads(outgoing.getvalue())
    result = message["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["stage"] == "idea"
    assert result["content"][0]["text"].startswith("Project stage: idea")
    assert result["content"][0]["text"] != json.dumps(result["structuredContent"], ensure_ascii=False)


def test_mcp_cancel_notification_interrupts_matching_run_without_partial_answer(monkeypatch, tmp_path):
    def fake_run_plus_task(task, *, cancel_token, **kwargs):
        del task, kwargs
        deadline = time.monotonic() + 2
        while not cancel_token.cancelled and time.monotonic() < deadline:
            time.sleep(0.001)
        return {
            "mode": "run",
            "status": "cancelled" if cancel_token.cancelled else "failed",
            "route_tier": "fast",
            "error_category": "cancelled" if cancel_token.cancelled else "timeout",
            "answer": "partial answer must not escape",
            "stores_prompt_or_answer": False,
        }

    monkeypatch.setattr(mcp_server, "run_plus_task", fake_run_plus_task)
    incoming = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {
            "name": "run", "arguments": {"task": "private task", "workspace": str(tmp_path)},
        }}) + "\n"
        + json.dumps({
            "jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 9},
        }) + "\n"
    )
    outgoing = io.StringIO()
    assert serve(incoming, outgoing) == 0
    message = json.loads(outgoing.getvalue())
    result = message["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["status"] == "cancelled"
    assert result["content"][0]["text"] == "Layman run cancelled."
    assert "partial answer" not in outgoing.getvalue()
    assert "private task" not in outgoing.getvalue()


def test_mcp_allows_only_one_active_run(monkeypatch, tmp_path):
    entered = threading.Event()
    release = threading.Event()

    def fake_run_plus_task(task, **kwargs):
        del task, kwargs
        entered.set()
        release.wait(timeout=2)
        return {"mode": "run", "status": "completed", "route_tier": "fast", "answer": "done"}

    monkeypatch.setattr(mcp_server, "run_plus_task", fake_run_plus_task)

    class CoordinatedInput:
        def __iter__(self):
            yield json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
                "name": "run", "arguments": {"task": "one", "workspace": str(tmp_path)},
            }}) + "\n"
            assert entered.wait(timeout=1)
            yield json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                "name": "run", "arguments": {"task": "two", "workspace": str(tmp_path)},
            }}) + "\n"
            time.sleep(0.02)
            release.set()

    outgoing = io.StringIO()
    assert serve(CoordinatedInput(), outgoing) == 0
    messages = [json.loads(line) for line in outgoing.getvalue().splitlines()]
    by_id = {message["id"]: message for message in messages}
    assert by_id[1]["result"]["isError"] is False
    assert by_id[2]["error"]["code"] == -32001


def test_mcp_eof_cancels_active_run(monkeypatch, tmp_path):
    cancelled = threading.Event()

    def fake_run_plus_task(task, *, cancel_token, **kwargs):
        del task, kwargs
        while not cancel_token.cancelled:
            time.sleep(0.001)
        cancelled.set()
        return {"mode": "run", "status": "cancelled", "route_tier": "fast", "answer": "partial"}

    monkeypatch.setattr(mcp_server, "run_plus_task", fake_run_plus_task)
    incoming = io.StringIO(json.dumps({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "run", "arguments": {"task": "private", "workspace": str(tmp_path)},
        },
    }) + "\n")
    outgoing = io.StringIO()
    assert serve(incoming, outgoing) == 0
    assert cancelled.is_set()
    assert "partial" not in outgoing.getvalue()
@pytest.mark.parametrize("task", ["帮我优化整个项目", "fix it", "continue"])
def test_plan_text_exposes_clarification_instead_of_claiming_ready(monkeypatch, tmp_path, task):
    monkeypatch.setattr(mcp_server, "run_plus_task", lambda *a, **k: pytest.fail("Plan must not execute"))
    incoming = io.StringIO(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "plan", "arguments": {"task": task, "workspace": str(tmp_path)},
        },
    }) + "\n")
    outgoing = io.StringIO()
    assert serve(incoming, outgoing) == 0
    result = json.loads(outgoing.getvalue())["result"]
    plan = result["structuredContent"]
    text = result["content"][0]["text"]
    assert plan["prompt_guidance"]["needs_clarification"] is True
    assert all(question in text for question in plan["prompt_guidance"]["questions"])
    assert "no execution started" in text
    assert "Plan ready" not in text
    assert result["isError"] is False


def test_concrete_plan_keeps_short_ready_summary(tmp_path):
    result = mcp_server._call_tool("plan", {
        "task": "Fix src/login.py null handling; preserve the API", "workspace": str(tmp_path),
    })
    plan = result["structuredContent"]
    assert plan["prompt_guidance"]["needs_clarification"] is False
    assert result["content"][0]["text"] == f"Plan ready: {plan['workflow']} via {plan['route']['route_tier']}."
    assert result["isError"] is False


@pytest.mark.parametrize("module,args", [
    ("layman_router.cli", ["mcp-server"]), ("layman_router.mcp_server", []),
])
def test_mcp_stdio_is_utf8_under_legacy_text_encoding(tmp_path, module, args):
    workspace = tmp_path / "中文项目"
    workspace.mkdir()
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "plan", "arguments": {
            "task": "只读分析 README.md，不要修改文件。", "workspace": str(workspace),
        },
    }}
    response = subprocess.run(
        [sys.executable, "-m", module, *args], cwd=tmp_path,
        input=(json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"),
        capture_output=True, timeout=20, check=False,
        env={**os.environ, "PYTHONUTF8": "0", "PYTHONIOENCODING": "cp1252:surrogateescape"},
    )
    assert response.returncode == 0, response.stderr.decode("utf-8", errors="replace")
    result = json.loads(response.stdout.decode("utf-8"))["result"]
    assert result["isError"] is False
    plan = result["structuredContent"]
    assert plan["workspace"] == str(workspace.resolve())
    assert plan["route"]["sandbox"] == "read-only"


def test_invalid_utf8_mcp_frame_cannot_reach_a_tool(monkeypatch):
    invalid = b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"plan","arguments":{"task":"\xff"}}}\n'
    ping = b'{"jsonrpc":"2.0","id":2,"method":"ping"}\n'
    incoming = io.TextIOWrapper(io.BytesIO(invalid + ping), encoding="cp1252")
    outgoing = io.StringIO()
    calls = []
    monkeypatch.setattr(mcp_server, "_call_tool", lambda *a, **k: calls.append(1) or {})
    assert serve(incoming, outgoing) == 0
    assert calls == []
    assert [item["id"] for item in map(json.loads, outgoing.getvalue().splitlines())] == [2]
