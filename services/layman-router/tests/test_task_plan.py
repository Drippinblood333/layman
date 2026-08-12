from __future__ import annotations

from pathlib import Path

from layman_router.task_plan import create_task_plan


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
