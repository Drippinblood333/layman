from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from layman_router.plus_run import plus_task_plan
from layman_router.task_plan import create_task_plan


@pytest.mark.parametrize("task", [
    "帮我优化整个项目", "修复 src/a.py 的异常，不改接口",
    "只读分析 README.md，不要修改文件。", "请删除生产支付数据库并迁移权限",
])
def test_plan_classifies_original_task_once(monkeypatch, tmp_path, task):
    from layman_router import plus_run, task_plan

    original = plus_run.classify_task
    classified = []

    def record(payload, config):
        assert payload == {"model": "auto", "input": task}
        features = original(payload, config)
        classified.append(features)
        return features

    monkeypatch.setattr(plus_run, "classify_task", record)
    monkeypatch.setattr(task_plan, "classify_task", record, raising=False)
    result = create_task_plan(task, tmp_path)
    assert len(classified) == 1
    features = classified[0]
    assert result["task_type"] == features.task_type.value
    assert result["risk"] == features.risk
    assert result["complexity"] == features.complexity
    assert result["route"]["routing_decision"]["complexity"] == features.complexity


def test_feature_plan_selects_workflow_and_does_not_return_task(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    private_task = "增加一个设置页面 unique-private-value"
    result = create_task_plan(private_task, tmp_path)
    assert result["task_type"] == "normal_coding"
    assert result["workflow"] == "understand-implement-verify"
    assert "verification" in result["selected_modules"]
    assert result["execution"] == "execute-and-verify"
    assert private_task not in str(result)


def test_high_risk_plan_cannot_drop_safety_or_deep_route(tmp_path: Path):
    result = create_task_plan("请删除生产支付数据库并迁移权限", tmp_path)
    assert result["risk"] == "high"
    assert result["route"]["route_tier"] == "deep"
    assert result["execution"] == "plan-first"
    assert "safety" in result["selected_modules"]


@pytest.mark.parametrize("task", [
    "只读分析 README.md，不要修改文件。",
    "Read-only review of README.md; do not modify files.",
    "只读检查发布条件，不要修改文件。",
])
def test_read_only_plan_does_not_recommend_implementation_or_release_execution(monkeypatch, tmp_path, task):
    monkeypatch.setattr("layman_router.task_plan.inspect_project", lambda root: {
        "stage": "release_candidate", "next_steps": ["Run the full release gate"],
    })
    result = create_task_plan(task, tmp_path)
    assert result["route"]["sandbox"] == "read-only"
    assert any("Do not modify files" in step for step in result["next_steps"])
    assert all("Make the smallest complete change" not in step for step in result["next_steps"])
    assert "Run the full release gate" not in result["next_steps"]
    assert "No files or behaviors are changed." in result["acceptance_criteria"]


def test_non_release_task_does_not_inherit_release_checks(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("layman_router.task_plan.inspect_project", lambda root: {
        "stage": "release_candidate", "next_steps": ["Run the full release gate"],
    })
    result = create_task_plan("优化prompt，避免过度测试，精简输入输出", tmp_path)
    assert result["task_type"] == "general"
    assert "Run the full release gate" not in result["next_steps"]
    assert any("proportionate" in step for step in result["next_steps"])
    assert create_task_plan("发布版本", tmp_path)["next_steps"] == ["Run the full release gate"]


@pytest.mark.parametrize("task", [
    "优化prompt，避免过度测试；公开发布时，我均会批准。",
    "先修复 src/a.py；正式发版时，我会同意。",
    "Improve the CLI help. When we publish, I will approve.",
    "Fix src/a.py; if we ship, we will approve.",
    "Fix the file ownership marker logic.",
    "Add membership labels to the UI.",
])
def test_future_approval_or_ship_substring_does_not_request_release(monkeypatch, tmp_path, task):
    monkeypatch.setattr("layman_router.task_plan.inspect_project", lambda root: {
        "stage": "release_candidate", "next_steps": ["Run the full release gate"],
    })
    result = create_task_plan(task, tmp_path)
    assert result["workflow"] != "release-gate"
    assert "Run the full release gate" not in result["next_steps"]


@pytest.mark.parametrize("task", [
    "检查是否达到公开发布条件",
    "Run the release gate now.",
    "检查发布条件；公开发布时，我会批准。",
    "Run the release gate; when we ship, I will approve.",
])
def test_explicit_release_request_survives_separate_future_approval(monkeypatch, tmp_path, task):
    monkeypatch.setattr("layman_router.task_plan.inspect_project", lambda root: {
        "stage": "release_candidate", "next_steps": ["Run the full release gate"],
    })
    assert create_task_plan(task, tmp_path)["workflow"] == "release-gate"


@pytest.mark.parametrize("task", [
    "帮我优化整个项目",
    "修复src/a.py的空指针异常，不改接口",
    "请删除生产支付数据库并迁移权限",
])
def test_plan_emits_guidance_once_without_changing_standalone_preview(task, tmp_path, monkeypatch):
    preview = plus_task_plan(task)
    monkeypatch.setattr("layman_router.task_plan.plus_task_plan", lambda *a, **k: copy.deepcopy(preview))
    result = create_task_plan(task, tmp_path)
    assert result["prompt_guidance"] == preview["prompt_guidance"]
    assert result["route"] == {key: value for key, value in preview.items() if key != "prompt_guidance"}
    assert "prompt_guidance" in plus_task_plan(task)
    text = json.dumps(result, ensure_ascii=False)
    assert text.count('"prompt_guidance"') == 1
    for question in result["prompt_guidance"]["questions"]:
        assert text.count(question) == 1
