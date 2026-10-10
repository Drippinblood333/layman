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
    "请修复登录时的空指针异常，不改变接口，运行已有回归测试",
    "增加一个设置页面", "不要优化整个项目，只修复src/a.py",
    "总结这句话：帮我优化整个项目", "```\nfix it\n```",
    "持续优化整个项目，目标是安装简单、保留原意、省token，每批改一项",
])
def test_concrete_or_quoted_requests_do_not_get_generic_clarification(task):
    assert prompt_guidance(task)["questions"] == []


def test_vague_plan_stops_before_execution_without_retaining_task(tmp_path):
    result = create_task_plan("帮我优化整个项目", tmp_path)
    assert result["execution"] == "plan-first"
    assert result["prompt_guidance"]["needs_clarification"] is True
    assert "帮我优化整个项目" not in str(result)
