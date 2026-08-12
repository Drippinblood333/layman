from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from layman_router.execution_control import CancellationToken, EventBudgetTracker, run_streaming_process
from layman_router.plus_run import plus_task_plan, run_plus_task


def test_plan_uses_deep_read_only_for_high_risk(router_config):
    plan = plus_task_plan("请分析生产支付数据库迁移风险", config=router_config)
    assert plan["route_tier"] == "deep"
    assert plan["model"] == "gpt-5.6-sol"
    assert plan["sandbox"] == "read-only"
    assert plan["expanded_file_budget"] == 20


def test_plan_uses_fast_budget_for_simple_summary(router_config):
    plan = plus_task_plan("请总结这段普通文字", config=router_config)
    assert plan["route_tier"] == "fast"
    assert plan["initial_file_budget"] == 3
    assert plan["tool_output_token_limit"] == 2000


def test_destructive_task_is_blocked_before_codex_without_explicit_authorization(tmp_path: Path):
    result = run_plus_task("Run rm -rf .", cwd=tmp_path, codex_path="codex")
    assert result["status"] == "blocked"
    assert result["execution_allowed"] is False
    assert result["sandbox"] == "read-only"
    assert result["attempts"] == []
    assert result["usage_incomplete"] is False
    assert result["error_category"] == "destructive_authorization_required"


def test_destructive_authorization_is_explicit_and_scoped(router_config):
    plan = plus_task_plan("git reset --hard HEAD~1", config=router_config, allow_destructive=True)
    assert plan["destructive"] is True
    assert plan["execution_allowed"] is True
    assert plan["sandbox"] == "workspace-write"


def test_run_uses_stdin_chatgpt_login_and_ephemeral_config(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-leak")
    monkeypatch.setenv("CODEX_THREAD_ID", "must-not-inherit")
    monkeypatch.setenv("CODEX_PERMISSION_PROFILE", "must-not-inherit")
    calls = []

    def fake_runner(command, **kwargs):
        calls.append((command, kwargs))
        if command[1:3] == ["login", "status"]:
            return subprocess.CompletedProcess(command, 0, stdout="Logged in using ChatGPT", stderr="")
        message_path = Path(command[command.index("--output-last-message") + 1])
        message_path.write_text("done", encoding="utf-8")
        event = json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 3}})
        return subprocess.CompletedProcess(command, 0, stdout=event, stderr="")

    result = run_plus_task("请总结内容", cwd=tmp_path, codex_path="codex", runner=fake_runner)
    command, kwargs = calls[-1]
    assert kwargs["input"] == "请总结内容"
    assert kwargs["cwd"] == tmp_path.resolve()
    assert "请总结内容" not in " ".join(command)
    assert "OPENAI_API_KEY" not in kwargs["env"]
    assert "CODEX_THREAD_ID" not in kwargs["env"]
    assert kwargs["env"]["CODEX_PERMISSION_PROFILE"] == ":workspace"
    assert "--ephemeral" in command
    assert "--ignore-user-config" not in command
    assert 'model_provider="openai"' in command
    assert 'model_auto_compact_token_limit=32000' in command
    assert 'default_permissions=":workspace"' in command
    assert any("must edit the workspace" in argument for argument in command)
    assert any("ceilings, not targets" in argument for argument in command)
    assert result["status"] == "completed"
    assert result["answer"] == "done"
    assert result["usage"] == {
        "input_tokens": 10,
        "cached_input_tokens": 0,
        "output_tokens": 3,
        "reasoning_tokens": 0,
    }
    assert result["usage_incomplete"] is False
    assert result["attempts"][0]["usage_available"] is True


def test_model_unavailable_only_falls_upward(tmp_path: Path):
    models = []

    def fake_runner(command, **kwargs):
        if command[1:3] == ["login", "status"]:
            return subprocess.CompletedProcess(command, 0, stdout="Logged in using ChatGPT", stderr="")
        model = command[command.index("-m") + 1]
        models.append(model)
        if len(models) == 1:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="model not found")
        message_path = Path(command[command.index("--output-last-message") + 1])
        message_path.write_text("fallback answer", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    result = run_plus_task("请总结内容", cwd=tmp_path, codex_path="codex", runner=fake_runner)
    assert models == ["gpt-5.6-luna", "gpt-5.6-terra"]
    assert result["route_tier"] == "balanced"
    assert result["fallback_used"] is True
    assert result["usage_incomplete"] is True


def test_fallback_accumulates_usage_from_every_attempt(tmp_path: Path):
    calls = 0

    def fake_runner(command, **kwargs):
        nonlocal calls
        if command[1:3] == ["login", "status"]:
            return subprocess.CompletedProcess(command, 0, stdout="Logged in using ChatGPT", stderr="")
        calls += 1
        usage_event = json.dumps({
            "type": "turn.completed",
            "usage": {"input_tokens": 10 * calls, "cached_input_tokens": calls, "output_tokens": 3 * calls},
        })
        tool_event = json.dumps({
            "type": "item.completed",
            "item": {"id": f"call-{calls}", "type": "command_execution", "command": "Get-Content src/a.py"},
        })
        events = usage_event + "\n" + tool_event
        if calls == 1:
            return subprocess.CompletedProcess(command, 1, stdout=events, stderr="model not found")
        message_path = Path(command[command.index("--output-last-message") + 1])
        message_path.write_text("fallback answer", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout=events, stderr="")

    result = run_plus_task("请总结内容", cwd=tmp_path, codex_path="codex", runner=fake_runner)
    assert result["usage"] == {
        "input_tokens": 30,
        "cached_input_tokens": 3,
        "output_tokens": 9,
        "reasoning_tokens": 0,
    }
    assert result["usage_incomplete"] is False
    assert [attempt["usage"]["input_tokens"] for attempt in result["attempts"]] == [10, 20]
    assert result["tool_calls"] == 2
    assert [attempt["tool_calls"] for attempt in result["attempts"]] == [1, 1]


def test_budget_stop_marks_usage_incomplete_and_hides_partial_answer(tmp_path: Path):
    def fake_runner(command, **kwargs):
        if command[1:3] == ["login", "status"]:
            return subprocess.CompletedProcess(command, 0, stdout="Logged in using ChatGPT", stderr="")
        message_path = Path(command[command.index("--output-last-message") + 1])
        message_path.write_text("partial answer", encoding="utf-8")
        events = [json.dumps({
            "type": "turn.completed",
            "usage": {"input_tokens": 10, "output_tokens": 2},
        })]
        events.extend(
            json.dumps({
                "type": "item.completed",
                "item": {"id": f"call-{index}", "type": "command_execution", "command": "Get-Content src/a.py"},
            })
            for index in range(13)
        )
        return subprocess.CompletedProcess(command, 0, stdout="\n".join(events), stderr="")

    result = run_plus_task("请总结内容", cwd=tmp_path, codex_path="codex", runner=fake_runner)
    assert result["status"] == "budget_exceeded"
    assert result["error_category"] == "budget_exceeded"
    assert result["usage_incomplete"] is True
    assert result["answer"] == ""
    assert result["tool_calls"] == 13


def test_stream_tracker_deduplicates_started_and_completed_tool_events():
    tracker = EventBudgetTracker()
    item = {"id": "call-1", "type": "command_execution", "command": "Get-Content src/example.py"}
    tracker.consume(json.dumps({"type": "item.started", "item": item}))
    tracker.consume(json.dumps({"type": "item.completed", "item": item}))
    assert tracker.tool_calls == 1
    assert tracker.unique_files_read == 1


def test_stream_tracker_counts_common_non_python_source_files():
    tracker = EventBudgetTracker()
    for index, path in enumerate(("src/main.go", "src/lib.rs", "src/App.java", "README.txt")):
        tracker.consume(json.dumps({
            "type": "item.completed",
            "item": {"id": str(index), "type": "file_read", "path": path},
        }))
    assert tracker.unique_files_read == 4


def test_streaming_process_stops_when_file_budget_is_exceeded(tmp_path: Path):
    script = (
        "import json,time\n"
        "for index in range(50):\n"
        " print(json.dumps({'type':'item.completed','item':{'id':str(index),'type':'command_execution',"
        "'command':f'Get-Content src/file{index}.py'}}), flush=True)\n"
        " time.sleep(0.01)\n"
    )
    result = run_streaming_process(
        [sys.executable, "-c", script],
        input_text="",
        cwd=tmp_path,
        env=os.environ.copy(),
        timeout_seconds=10,
        file_limit=1,
        tool_call_limit=100,
    )
    assert result.stop_reason == "budget_exceeded"
    assert result.unique_files_read > 1


def test_streaming_process_stops_cancelled_process_tree(tmp_path: Path):
    token = CancellationToken()
    timer = threading.Timer(0.1, token.cancel)
    timer.start()
    started = time.monotonic()
    try:
        result = run_streaming_process(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            input_text="",
            cwd=tmp_path,
            env=os.environ.copy(),
            timeout_seconds=10,
            file_limit=1,
            tool_call_limit=1,
            cancel_token=token,
        )
    finally:
        timer.cancel()
    assert result.stop_reason == "cancelled"
    assert time.monotonic() - started < 5
