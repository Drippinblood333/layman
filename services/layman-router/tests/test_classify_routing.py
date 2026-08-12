from __future__ import annotations

from layman_router.classify import classify_task
from layman_router.models import RouteTier, TaskType
from layman_router.routing import apply_route, decide_route, explicit_model_decision, fallback_decision


def test_summary_routes_fast(router_config):
    payload = {"model": "auto", "input": "请总结这段发布说明"}
    features = classify_task(payload, router_config)
    decision = decide_route(features, router_config)
    assert features.task_type == TaskType.SUMMARY
    assert decision.route_tier == RouteTier.FAST
    assert decision.selected_model == "gpt-5.6-luna"


def test_high_risk_routes_deep(router_config):
    payload = {"model": "auto", "input": "请审查生产环境支付认证数据库迁移的安全风险"}
    features = classify_task(payload, router_config)
    decision = decide_route(features, router_config)
    assert features.risk == "high"
    assert decision.route_tier == RouteTier.DEEP


def test_tool_heavy_fast_task_is_raised_to_balanced(router_config):
    payload = {"model": "auto", "input": "总结结果", "tools": [{"type": "function", "name": "read"}, {"type": "function", "name": "search"}]}
    decision = decide_route(classify_task(payload, router_config), router_config)
    assert decision.route_tier == RouteTier.BALANCED


def test_high_risk_floor_beats_fast_metadata_override(router_config):
    payload = {"model": "auto", "input": "请总结生产支付认证事故", "metadata": {"layman_route": "fast"}}
    decision = decide_route(classify_task(payload, router_config), router_config, payload["metadata"])
    assert decision.route_tier == RouteTier.DEEP
    assert "high-risk safety floor overrides lower route" in decision.route_reason


def test_metadata_override_wins(router_config):
    payload = {"model": "auto", "input": "总结结果", "metadata": {"layman_route": "deep"}}
    decision = decide_route(classify_task(payload, router_config), router_config, payload["metadata"])
    assert decision.route_tier == RouteTier.DEEP
    assert decision.route_reason[0] == "request override: deep"


def test_auto_route_replaces_only_policy_fields(router_config):
    payload = {
        "model": "auto",
        "input": "实现一个小函数",
        "tools": [{"type": "function", "name": "read"}],
        "previous_response_id": "resp_previous",
        "reasoning": {"effort": "high", "summary": "auto"},
        "max_output_tokens": 1000,
    }
    decision = decide_route(classify_task(payload, router_config), router_config)
    routed = apply_route(payload, decision)
    assert routed["model"] == "gpt-5.6-terra"
    assert routed["reasoning"] == {"effort": "medium", "summary": "auto"}
    assert routed["max_output_tokens"] == 1000
    assert routed["tools"] == payload["tools"]
    assert routed["previous_response_id"] == "resp_previous"


def test_explicit_model_is_unchanged(router_config):
    payload = {"model": "custom-model", "input": "hello", "reasoning": {"effort": "low"}}
    decision = explicit_model_decision(payload, router_config)
    assert not decision.automatic
    assert apply_route(payload, decision) == payload
    assert fallback_decision(decision, router_config) is None


def test_prompt_hash_does_not_contain_prompt(router_config):
    secret = "private source code phrase"
    features = classify_task({"model": "auto", "input": secret}, router_config)
    assert len(features.prompt_hash) == 64
    assert secret not in features.prompt_hash
