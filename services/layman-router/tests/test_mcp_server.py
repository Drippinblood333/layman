from __future__ import annotations

import io
import json

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
