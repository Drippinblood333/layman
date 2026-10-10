from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from layman_router.execution_control import (
    CancellationToken,
    EventBudgetTracker,
    StreamedProcessResult,
    run_streaming_process,
)
from layman_router.models import RouteTier
from layman_router.plus_run import (
    POLICIES,
    _execution_contract,
    plus_task_plan,
    run_plus_task,
)


def test_command_failures_use_only_completed_envelope_and_deduplicate():
    tracker = EventBudgetTracker()
    item = {"id": "cmd-1", "type": "command_execution", "exit_code": 1,
            "command": "secret command", "aggregated_output": "private output"}
    tracker.consume(json.dumps({"type": "item.started", "item": item}))
    assert tracker.command_failures == 0
    for _ in range(2):
        tracker.consume(json.dumps({"type": "item.completed", "item": item}))
    assert tracker.command_failures == 1
    tracker.consume(json.dumps({"type": "item.completed", "item": {
        "type": "agent_message", "text": "spawn EPERM", "nested": item}}))
    assert tracker.command_failures == 1


def test_file_change_action_counts_once_across_lifecycle():
    tracker = EventBudgetTracker()
    item = {"id": "patch-1", "type": "file_change", "status": "completed",
            "changes": [{"path": "src/target.py", "kind": "update"}]}
    for event_type in ("item.started", "item.completed", "item.completed"):
        tracker.consume(json.dumps({"type": event_type, "item": item}))
    assert tracker.tool_calls == 1
    assert tracker.command_failures == 0


def test_patch_only_execution_is_not_mislabelled_as_no_tool_action(tmp_path):
    def runner(command, **kwargs):
        if command[1:3] == ["login", "status"]:
            return subprocess.CompletedProcess(command, 0, stdout="Logged in using ChatGPT", stderr="")
        Path(command[command.index("--output-last-message") + 1]).write_text("modified", encoding="utf-8")
        events = [
            {"type": "item.completed", "item": {"id": "patch-1", "type": "file_change",
             "status": "completed", "changes": [{"path": "src/target.py", "kind": "update"}]}},
            {"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 3}},
        ]
        return subprocess.CompletedProcess(command, 0, stdout="\n".join(map(json.dumps, events)), stderr="")

    result = run_plus_task("修复 src/target.py 的顺序", cwd=tmp_path, codex_path=sys.executable, runner=runner)
    assert result["tool_calls"] == 1
    assert result["error_category"] is None


@pytest.mark.parametrize("exit_code", [0, None, True, "1"])
def test_command_failure_count_rejects_missing_success_or_invalid_exit(exit_code):
    tracker = EventBudgetTracker()
    tracker.consume(json.dumps({"type": "item.completed", "item": {
        "id": "cmd", "type": "command_execution", "exit_code": exit_code}}))
    assert tracker.command_failures == 0


@pytest.mark.parametrize("tier", list(RouteTier))
@pytest.mark.parametrize("read_only", [True, False])
def test_short_execution_contract_preserves_scope_safety_and_soft_budget(tier, read_only):
    policy = POLICIES[tier]
    contract = _execution_contract(tier, policy, read_only=read_only, workflow="fix")
    assert "Preserve request/scope" in contract
    assert f"{policy.initial_files} initially; {policy.expanded_files} only for a concrete evidence gap" in contract
    assert f"at most {policy.tool_calls} tool calls" in contract
    assert "Search symbols/tests first" in contract
    assert f"Soft upper guide {policy.final_output_token_target}" in contract
    assert "never pad or truncate needed detail" in contract
    assert "outcome, verification, risks/next step" in contract
    if read_only:
        assert "do not modify files" in contract
        assert "must edit" not in contract
    else:
        assert "If implementation is requested, you must edit the workspace and verify now" in contract
        assert "Make only requested changes" in contract


def test_vague_task_is_blocked_before_any_codex_call(tmp_path):
    def forbidden_runner(*args, **kwargs):
        pytest.fail("Clarification must precede even CLI login/version checks")

    result = run_plus_task("帮我优化整个项目", cwd=tmp_path, execute=True, runner=forbidden_runner)
    assert result["status"] == "blocked"
    assert result["error_category"] == "prompt_clarification_required"
    assert result["attempts"] == []
    assert not any(result["usage"].values())
    assert result["tool_calls"] == 0
    assert "帮我优化整个项目" not in str(result)


@pytest.mark.parametrize("workflow", ["understand-implement-verify", "reproduce-fix-verify", "discover-test-gaps-verify"])
def test_development_safety_is_scoped_without_unproven_reuse_advice(workflow):
    policy = POLICIES[RouteTier.BALANCED]
    writable = _execution_contract(RouteTier.BALANCED, policy, read_only=False, workflow=workflow)
    assert "Reuse project code > stdlib/platform > installed deps" not in writable
    assert "no speculative abstractions" not in writable
    assert "Keep validation/errors/accessibility; check affected callers" in writable
    assert "Preserve request/scope" in writable
    assert "must edit the workspace and verify now" in writable
    readonly = _execution_contract(RouteTier.BALANCED, policy, read_only=True, workflow=workflow)
    assert "Reuse project code" not in readonly
    assert "do not modify files" in readonly


@pytest.mark.parametrize("workflow", ["scope-execute-verify", "inspect-update-check-links", "release-gate"])
def test_non_development_contract_does_not_load_lean_rules(workflow):
    assert "Reuse project code" not in _execution_contract(
        RouteTier.FAST, POLICIES[RouteTier.FAST], read_only=False, workflow=workflow,
    )


def test_vague_dry_run_reports_block_without_model_execution(tmp_path):
    result = run_plus_task("fix it", cwd=tmp_path, execute=False, codex_path="missing")
    assert result["mode"] == "dry-run"
    assert result["execution_allowed"] is False
    assert result["prompt_guidance"]["needs_clarification"] is True


@pytest.mark.parametrize("task,expected", [
    ("修复 src/target.py 中 unique 的顺序", "needs_verification"),
    ("修复 src/target.py 中 unique 的顺序，不要修改接口。", "needs_verification"),
    ("修复 src/target.py 中 unique 的顺序，不要修改其他文件。", "needs_verification"),
    ("Fix src/target.py; do not change the API.", "needs_verification"),
    ("Fix src/target.py; do not modify other files.", "needs_verification"),
    ("Fix src/target.py; do not change the API; review only.", "completed"),
    ("修复 src/target.py 的方案，不要修改接口，不要修改文件。", "completed"),
    ("为 src/target.py 添加 tests/test_target.py", "needs_verification"),
    ("解释 src/target.py 的代码，不要修改文件", "completed"),
    ("只分析 src/target.py 的修复方案，不要修改文件", "completed"),
    ("请总结内容", "completed"),
])
def test_named_file_execution_without_tools_is_not_reported_as_delivered(tmp_path, task, expected):
    executions = []

    def fake_runner(command, **kwargs):
        if command[1:3] == ["login", "status"]:
            return subprocess.CompletedProcess(command, 0, stdout="Logged in using ChatGPT", stderr="")
        assert kwargs["input"] == task
        executions.append(command)
        Path(command[command.index("--output-last-message") + 1]).write_text("advice only", encoding="utf-8")
        event = json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 3}})
        return subprocess.CompletedProcess(command, 0, stdout=event, stderr="")

    result = run_plus_task(task, cwd=tmp_path, codex_path=sys.executable, runner=fake_runner)
    assert result["status"] == expected
    assert len(executions) == 1
    assert result["tool_calls"] == 0
    assert result["usage_incomplete"] is False
    if expected == "needs_verification":
        assert result["error_category"] == "workspace_execution_not_observed"
        assert "不能确认任务已完成" in result["answer"]
        assert result["attempts"][0]["status"] == "completed"


@pytest.mark.parametrize("tool_calls,expected", [(0, "needs_verification"), (1, "completed")])
@pytest.mark.parametrize("task", [
    "修复 src/target.py 的顺序",
    "修复 src/target.py 的顺序，不要修改接口。",
    "Fix src/target.py; do not modify other files.",
])
def test_streamed_named_file_completion_uses_observed_tool_metadata(monkeypatch, tmp_path, tool_calls, expected, task):
    monkeypatch.setattr("layman_router.plus_run.codex_login_status", lambda *a, **k: {"available": True, "chatgpt_login": True})
    executions = []

    def fake_stream(command, **kwargs):
        assert kwargs["input_text"] == task
        executions.append(command)
        Path(command[command.index("--output-last-message") + 1]).write_text("response", encoding="utf-8")
        return StreamedProcessResult(
            returncode=0, stderr="", usage={"input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 3, "reasoning_tokens": 0},
            usage_available=True, tool_calls=tool_calls, unique_files_read=0, compactions=0,
            command_failures=tool_calls,
        )

    monkeypatch.setattr("layman_router.plus_run.run_streaming_process", fake_stream)
    result = run_plus_task(task, cwd=tmp_path, codex_path=sys.executable)
    assert result["status"] == expected
    assert result["tool_calls"] == tool_calls
    assert result["command_failures"] == tool_calls
    assert result["attempts"][0]["command_failures"] == tool_calls
    assert len(executions) == 1
    assert result["usage"]["input_tokens"] == 10


def test_plan_uses_deep_read_only_for_high_risk(router_config):
    plan = plus_task_plan("请分析生产支付数据库迁移风险", config=router_config)
    assert plan["route_tier"] == "deep"
    assert plan["model"] == "gpt-6-astra"
    assert plan["sandbox"] == "read-only"
    assert plan["expanded_file_budget"] == 20


def test_plan_uses_fast_budget_for_simple_summary(router_config):
    plan = plus_task_plan("请总结这段普通文字", config=router_config)
    assert plan["route_tier"] == "fast"
    assert plan["initial_file_budget"] == 3
    assert plan["tool_output_token_limit"] == 2000


def test_plan_reports_structured_uncalibrated_decision_and_router_overhead(router_config):
    plan = plus_task_plan("请总结这段普通文字", config=router_config)
    decision = plan["routing_decision"]
    overhead = plan["router_overhead"]
    assert decision["task_type"] == "summary"
    assert decision["selected_model"] == "gpt-6-luna"
    assert decision["reasoning_effort"] == "low"
    assert decision["calibration_state"] == "heuristic_uncalibrated"
    assert "confidence" not in decision
    assert overhead["feature_extraction_ms"] >= 0
    assert overhead["policy_decision_ms"] >= 0
    assert overhead["router_compute_ms"] == (
        overhead["feature_extraction_ms"] + overhead["policy_decision_ms"]
    )
    assert overhead["total_routing_preflight_ms"] >= overhead["router_compute_ms"]


def test_destructive_task_is_blocked_before_codex_without_explicit_authorization(tmp_path: Path):
    result = run_plus_task("Run rm -rf .", cwd=tmp_path, codex_path=sys.executable)
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

    result = run_plus_task("请总结内容", cwd=tmp_path, codex_path=sys.executable, runner=fake_runner)
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

    result = run_plus_task("请总结内容", cwd=tmp_path, codex_path=sys.executable, runner=fake_runner)
    assert models == ["gpt-6-luna", "gpt-6.1-sol"]
    assert result["route_tier"] == "balanced"
    assert result["fallback_used"] is True
    assert result["usage_incomplete"] is True


def test_attempt_limit_prevents_a_fallback_launch(tmp_path: Path):
    models = []

    def fake_runner(command, **kwargs):
        if command[1:3] == ["login", "status"]:
            return subprocess.CompletedProcess(command, 0, stdout="Logged in using ChatGPT", stderr="")
        models.append(command[command.index("-m") + 1])
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="model not found")

    result = run_plus_task("请总结内容", cwd=tmp_path, codex_path=sys.executable, runner=fake_runner, max_model_attempts=1)
    assert models == ["gpt-6-luna"]
    assert len(result["attempts"]) == 1
    assert result["status"] == "failed"
    assert result["fallback_used"] is False


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

    result = run_plus_task("请总结内容", cwd=tmp_path, codex_path=sys.executable, runner=fake_runner)
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

    result = run_plus_task("请总结内容", cwd=tmp_path, codex_path=sys.executable, runner=fake_runner)
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


@pytest.mark.parametrize("task", [
    "在 src/target.py 实现 paginate(values, page, size)，非法页码抛出 ValueError。",
    "保留原意：中文🙂与引号\"、反斜线\\。\r\n第二行\n末行无换行",
])
def test_real_streamed_child_receives_same_utf8_task_and_cwd_as_direct(tmp_path: Path, task: str):
    # No model/login: the child validates the real pipe payload after EOF.
    workspace = tmp_path / "中文 workspace"
    workspace.mkdir()
    # Both existing text-mode transports apply the platform's newline mapping.
    # Compare against that payload rather than claiming byte-identical line ends.
    digest = hashlib.sha256(task.replace("\n", os.linesep).encode("utf-8")).hexdigest()
    script = (
        "import hashlib,json,os,sys\n"
        "payload=sys.stdin.buffer.read()\n"
        "assert hashlib.sha256(payload).hexdigest()==sys.argv[1]\n"
        "assert os.path.samefile(os.getcwd(),sys.argv[2])\n"
        "print(json.dumps({'type':'turn.completed','usage':"
        "{'input_tokens':1,'output_tokens':1}}),flush=True)\n"
    )
    command = [sys.executable, "-c", script, digest, str(workspace)]
    direct = subprocess.run(command, input=task, capture_output=True, text=True,
                            encoding="utf-8", cwd=workspace, timeout=10, check=False)
    streamed = run_streaming_process(
        command, input_text=task, cwd=workspace, env=os.environ.copy(),
        timeout_seconds=10, file_limit=1, tool_call_limit=1,
    )
    assert direct.returncode == streamed.returncode == 0
    assert streamed.stop_reason is None
    assert streamed.usage_available is True
    assert streamed.usage["input_tokens"] == streamed.usage["output_tokens"] == 1
    assert streamed.tool_calls == 0


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


def test_streaming_process_exports_only_numeric_command_failures(tmp_path: Path):
    event = {"type": "item.completed", "item": {
        "id": "cmd", "type": "command_execution", "exit_code": 1,
        "command": "private-command", "aggregated_output": "private-output"}}
    script = "import json; print(" + repr(json.dumps(event)) + ")"
    result = run_streaming_process(
        [sys.executable, "-c", script], input_text="", cwd=tmp_path,
        env=os.environ.copy(), timeout_seconds=10, file_limit=1, tool_call_limit=1,
    )
    assert result.returncode == 0
    assert result.command_failures == 1
    assert result.stop_reason is None
    assert "private-command" not in repr(result)
    assert "private-output" not in repr(result)


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
