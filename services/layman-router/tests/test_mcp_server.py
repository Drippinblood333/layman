from __future__ import annotations

import io
import json
import threading
import time

from layman_router import mcp_server
from layman_router.mcp_server import serve


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
