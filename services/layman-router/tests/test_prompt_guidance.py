from __future__ import annotations

import pytest
from layman_router.prompt_guidance import prompt_guidance
from layman_router.task_plan import create_task_plan


@pytest.mark.parametrize("task", ["帮我优化整个项目", "请完善我的项目。", "重构一下", "fix it", "please improve the whole project"])
def test_vague_requests_get_at_most_two_questions_without_rewriting(task):
    result = prompt_guidance(task)
    assert result["needs_clarification"] is True
    assert len(result["questions"]) == 2
    assert result["rewritten"] is False
    assert result["model_calls"] == 0
    assert task not in str(result)


@pytest.mark.parametrize("task", [
    "帮我优化整个项目吧", "请修复一下，谢谢！", "优化这个项目，谢谢。",
    "fix it, please", "improve my project, please.",
])
def test_polite_suffix_does_not_make_an_unspecified_request_actionable(task):
    result = prompt_guidance(task)
    assert result["needs_clarification"] is True
    assert len(result["questions"]) == 2
    assert result["rewritten"] is False
    assert result["model_calls"] == 0


@pytest.mark.parametrize("task", [
    "请修复登录时的空指针异常，不改变接口，运行已有回归测试",
    "增加一个设置页面", "不要优化整个项目，只修复src/a.py",
    "总结这句话：帮我优化整个项目", "```\nfix it\n```",
    "持续优化整个项目，目标是安装简单、保留原意、省token，每批改一项",
    "优化这个项目，安装改成一步完成，谢谢。",
    "fix this error in src/a.py, please.", "把按钮文字改成‘优化整个项目吧’",
])
def test_concrete_or_quoted_requests_do_not_get_generic_clarification(task):
    assert prompt_guidance(task)["questions"] == []


def test_vague_plan_stops_before_execution_without_retaining_task(tmp_path):
    result = create_task_plan("帮我优化整个项目", tmp_path)
    assert result["execution"] == "plan-first"
    assert result["prompt_guidance"]["needs_clarification"] is True
    assert "帮我优化整个项目" not in str(result)
    assert result["route"]["execution_allowed"] is False
    assert len(result["next_steps"]) == 1
    assert "resubmit the original request" in result["next_steps"][0]
    assert "no execution has started" in result["next_steps"][0]


def test_concrete_plan_keeps_normal_implementation_next_steps(tmp_path):
    result = create_task_plan("修复src/a.py的空指针异常，不改接口", tmp_path)
    assert result["prompt_guidance"]["needs_clarification"] is False
    assert len(result["next_steps"]) == 3
    assert "Make the smallest complete change" in result["next_steps"][1]


def test_mcp_vague_run_exposes_questions_without_model_execution(monkeypatch, tmp_path):
    from layman_router import mcp_server

    monkeypatch.setattr("layman_router.plus_run.find_codex", lambda *a, **k: pytest.fail("No model preflight permitted"))
    result = mcp_server._call_tool("run", {"task": "帮我优化整个项目", "workspace": str(tmp_path)})
    assert result["isError"] is True
    assert result["structuredContent"]["error_category"] == "prompt_clarification_required"
    assert "具体结果" in result["content"][0]["text"]


def test_polite_vague_run_stops_before_login_and_preserves_concrete_followup(monkeypatch, tmp_path):
    from layman_router.plus_run import run_plus_task

    monkeypatch.setattr("layman_router.plus_run.find_codex", lambda *a, **k: pytest.fail("No model preflight permitted"))
    result = run_plus_task("帮我优化整个项目吧", cwd=tmp_path)
    assert result["error_category"] == "prompt_clarification_required"
    assert result["attempts"] == []
    concrete = "优化这个项目，安装改成一步完成，谢谢。"
    preview = run_plus_task(concrete, cwd=tmp_path, execute=False)
    assert preview["prompt_guidance"]["needs_clarification"] is False
