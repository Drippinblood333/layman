from __future__ import annotations

import pytest
from layman_router.prompt_guidance import prompt_guidance
from layman_router.task_plan import create_task_plan


@pytest.mark.parametrize("task", [
    "继续", "请继续吧", "接着做", "继续之前的任务", "继续上一个任务，谢谢！",
    "continue", "please continue", "go on", "continue the previous task", "carry on, please.",
])
def test_context_only_continuations_request_missing_goal_without_rewriting(task):
    result = prompt_guidance(task)
    assert result["needs_clarification"] is True
    assert len(result["questions"]) == 2
    assert "原始任务" in result["questions"][0]
    assert result["rewritten"] is False
    assert result["model_calls"] == 0


@pytest.mark.parametrize("task", [
    "继续修复 src/a.py 的登录错误，不改接口", "Continue fixing src/a.py; keep the API unchanged.",
    "把按钮文字改为‘继续’", 'Translate "continue" into Chinese.',
    "```\ncontinue\n```", "继续优化整个项目，目标是安装简单、省 token，每批改一项",
])
def test_concrete_or_quoted_continuations_keep_the_original_scope(task):
    assert prompt_guidance(task)["needs_clarification"] is False


@pytest.mark.parametrize("task", ["继续", "continue the previous task"])
def test_context_only_run_stops_before_cli_preflight(monkeypatch, tmp_path, task):
    from layman_router.plus_run import run_plus_task

    monkeypatch.setattr("layman_router.plus_run.find_codex", lambda *a, **k: pytest.fail("No model preflight permitted"))
    result = run_plus_task(task, cwd=tmp_path)
    assert result["error_category"] == "prompt_clarification_required"
    assert result["attempts"] == []
    assert result["tool_calls"] == 0


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
    "请帮我优化整个项目", "帮我修个bug", "请修复这个错误，谢谢！",
    "解决问题", "fix the bug, please", "please fix bugs",
])
def test_objectless_bug_requests_need_details_without_rewriting(task):
    result = prompt_guidance(task)
    assert result["needs_clarification"] is True
    assert len(result["questions"]) == 2
    assert result["rewritten"] is False
    assert result["model_calls"] == 0


@pytest.mark.parametrize("task", [
    "请帮我修复 src/login.py 登录报错，不改接口",
    "修复这个错误：ValueError 在 src/a.py 第12行出现",
    "fix the bug in src/login.py; preserve the public API",
    "把按钮文字改成‘帮我修个bug’", "总结这句话：fix the bug",
])
def test_bug_wording_with_context_or_quotation_is_not_blocked(task):
    assert prompt_guidance(task)["needs_clarification"] is False


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


@pytest.mark.parametrize("task", ["帮我优化整个项目", "帮我修个bug", "fix the bug, please"])
def test_mcp_vague_run_exposes_questions_without_model_execution(monkeypatch, tmp_path, task):
    from layman_router import mcp_server

    monkeypatch.setattr("layman_router.plus_run.find_codex", lambda *a, **k: pytest.fail("No model preflight permitted"))
    result = mcp_server._call_tool("run", {"task": task, "workspace": str(tmp_path)})
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
