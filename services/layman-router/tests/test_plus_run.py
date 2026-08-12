from __future__ import annotations

import json
import subprocess
from pathlib import Path

from layman_router.plus_run import plus_task_plan, run_plus_task


def test_plan_uses_deep_read_only_for_high_risk(router_config):
    plan = plus_task_plan("请分析生产支付数据库迁移风险", config=router_config)
    assert plan["route_tier"] == "deep"
    assert plan["model"] == "gpt-5.6-sol"
    assert plan["sandbox"] == "read-only"
    assert plan["expanded_file_budget"] == 32


def test_plan_uses_fast_budget_for_simple_summary(router_config):
    plan = plus_task_plan("请总结这段普通文字", config=router_config)
    assert plan["route_tier"] == "fast"
    assert plan["initial_file_budget"] == 6
    assert plan["tool_output_token_limit"] == 4000


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
    assert result["status"] == "completed"
    assert result["answer"] == "done"


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
