from __future__ import annotations

import pytest
from layman_router.classify import classify_task
from layman_router.models import ProjectConfig, RouteTier, TaskType, TierConfig
from layman_router.routing import (
    apply_route,
    decide_route,
    explicit_model_decision,
    fallback_decision,
)


@pytest.mark.parametrize("task", [
    "项目安装简单，体积小，上手简单，优化prompt，避免过度测试，精简输入输出，节省token",
    "避免过度测试", "不要不必要的测试", "减少过量测试", "avoid excessive testing",
])
def test_efficiency_constraints_do_not_request_testing(router_config, task):
    assert classify_task({"model": "auto", "input": task}, router_config).task_type == TaskType.GENERAL


@pytest.mark.parametrize("task", ["避免过度测试，但请增加必要测试", "请编写单元测试，避免过度测试"])
def test_efficiency_constraints_preserve_positive_test_requests(router_config, task):
    assert classify_task({"model": "auto", "input": task}, router_config).task_type == TaskType.TESTING


def test_summary_routes_fast(router_config):
    payload = {"model": "auto", "input": "请总结这段发布说明"}
    features = classify_task(payload, router_config)
    decision = decide_route(features, router_config)
    assert features.task_type == TaskType.SUMMARY
    assert decision.route_tier == RouteTier.FAST
    assert decision.selected_model == "gpt-6-luna"
    assert decision.output_verbosity == "low"


def test_astra_and_sol_reject_none_reasoning(router_config):
    for tier in ("balanced", "deep"):
        values = router_config.tiers[tier].model_dump()
        values["reasoning_effort"] = "none"
        with pytest.raises(ValueError, match="does not support"):
            TierConfig.model_validate(values)


def test_high_risk_routes_deep(router_config):
    payload = {"model": "auto", "input": "请审查生产环境支付认证数据库迁移的安全风险"}
    features = classify_task(payload, router_config)
    decision = decide_route(features, router_config)
    assert features.risk == "high"
    assert decision.route_tier == RouteTier.DEEP


def test_available_tool_count_alone_does_not_raise_fast_task(router_config):
    payload = {"model": "auto", "input": "总结结果", "tools": [{"type": "function", "name": "read"}, {"type": "function", "name": "search"}]}
    decision = decide_route(classify_task(payload, router_config), router_config)
    assert decision.route_tier == RouteTier.FAST


def test_explicit_multi_source_tool_intent_raises_fast_task(router_config):
    payload = {
        "model": "auto",
        "input": "请总结并交叉检查两个资料源",
        "tools": [{"type": "function", "name": "read"}, {"type": "function", "name": "search"}],
    }
    decision = decide_route(classify_task(payload, router_config), router_config)
    assert decision.route_tier == RouteTier.BALANCED


def test_destructive_commands_are_high_risk_and_detected(router_config):
    commands = (
        "Run rm -rf .",
        "rm -fr build",
        "请执行 rm -rf build",
        "rm -r build",
        "Remove-Item build -Recurse",
        "Remove-Item build -Force -Recurse",
        "git reset --hard HEAD~1",
        "git clean -d -f",
        "git clean -fd",
        "git clean -fdx",
        "git restore -- README.md",
        "git restore .",
        "git checkout .",
        "git branch -D old-work",
        "TRUNCATE TABLE users",
        "wipe the repository",
        "force push main",
        "remove all user accounts",
    )
    for command in commands:
        features = classify_task({"model": "auto", "input": command}, router_config)
        assert features.destructive, command
        assert features.risk == "high", command


def test_read_only_mentions_and_negated_risk_do_not_false_positive(router_config):
    for task in (
        "Fix the README; do not delete files.",
        "Review this code; no production access is needed.",
        "只读评审 rm -rf . 的风险，不要执行。",
        "Fix the README; do not run rm -rf build.",
        "Review the output of git clean -nfd without executing it.",
    ):
        features = classify_task({"model": "auto", "input": task}, router_config)
        assert not features.destructive, task
        assert features.risk == "low", task


def test_latest_user_task_drives_type_while_active_calls_keep_safety(router_config):
    payload = {
        "model": "auto",
        "input": [
            {"role": "user", "content": "请评审生产支付迁移"},
            {"role": "assistant", "content": "done"},
            {"role": "user", "content": "请总结最终结论"},
        ],
    }
    features = classify_task(payload, router_config)
    assert features.task_type == TaskType.SUMMARY
    assert features.risk == "low"


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
        "text": {"format": {"type": "text"}, "verbosity": "high"},
        "max_output_tokens": 1000,
    }
    decision = decide_route(classify_task(payload, router_config), router_config)
    routed = apply_route(payload, decision)
    assert routed["model"] == "gpt-6.1-sol"
    assert routed["reasoning"] == {"effort": "medium", "summary": "auto"}
    assert routed["text"] == {"format": {"type": "text"}, "verbosity": "low"}
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


def test_policy_pending_deep_task_fast_metadata_override_currently_wins(router_config):
    """Characterization only: whether deep task intent should beat a fast override is unresolved."""
    payload = {
        "model": "auto",
        "input": "Please design the architecture and module boundaries for this system",
        "metadata": {"layman_route": "fast"},
    }
    features = classify_task(payload, router_config)
    decision = decide_route(features, router_config, payload["metadata"])
    assert features.task_type == TaskType.ARCHITECTURE
    assert features.risk == "medium"
    assert decision.route_tier == RouteTier.FAST


def test_policy_pending_high_complexity_low_budget_currently_routes_fast(router_config):
    """Characterization only: the low-budget demotion currently runs after complexity escalation."""
    payload = {
        "model": "auto",
        "input": "Summarize this report: " + ("ordinary background material " * 500),
        "metadata": {"layman_budget": "low"},
    }
    features = classify_task(payload, router_config)
    decision = decide_route(features, router_config, payload["metadata"])
    assert features.complexity == "high"
    assert features.risk == "low"
    assert decision.route_tier == RouteTier.FAST
    assert "high input complexity" in decision.route_reason
    assert "low budget and low risk" in decision.route_reason


def test_short_confirmation_inherits_recent_destructive_user_intent(router_config):
    for followup in (
        "do it",
        "do it now",
        "go ahead",
        "proceed",
        "continue",
        "execute it",
        "run it",
        "yes, do it",
        "继续",
        "继续执行",
        "执行吧",
        "确认执行",
        "开始吧",
        "就这么做",
    ):
        payload = {
            "model": "auto",
            "input": [
                {"role": "user", "content": "Run git reset --hard HEAD~1"},
                {"role": "assistant", "content": "That is destructive and needs confirmation."},
                {"role": "user", "content": followup},
            ],
        }
        features = classify_task(payload, router_config)
        decision = decide_route(features, router_config)
        assert features.risk == "high", followup
        assert features.destructive is True, followup
        assert decision.route_tier == RouteTier.DEEP, followup


def test_confirmation_inherits_destructive_production_user_deletion(router_config):
    payload = {
        "model": "auto",
        "input": [
            {"role": "user", "content": "删除生产用户"},
            {"role": "assistant", "content": "请确认。"},
            {"role": "user", "content": "确认执行"},
        ],
    }
    features = classify_task(payload, router_config)
    assert features.risk == "high"
    assert features.destructive is True


def test_confirmation_inherits_high_risk_secret_rotation_without_destructive_label(router_config):
    payload = {
        "model": "auto",
        "input": [
            {"role": "user", "content": "production authentication secret rotation"},
            {"role": "assistant", "content": "Ready when approved."},
            {"role": "user", "content": "continue"},
        ],
    }
    features = classify_task(payload, router_config)
    assert features.risk == "high"
    assert features.destructive is False


def test_explanation_continuation_does_not_inherit_destructive_intent(router_config):
    payload = {
        "model": "auto",
        "input": [
            {"role": "user", "content": "解释 rm -rf 为什么危险，不要执行"},
            {"role": "assistant", "content": "这是递归删除命令。"},
            {"role": "user", "content": "继续解释"},
        ],
    }
    features = classify_task(payload, router_config)
    assert features.risk == "low"
    assert features.destructive is False


def test_negated_destructive_intent_is_not_inherited(router_config):
    payload = {
        "model": "auto",
        "input": [
            {"role": "user", "content": "不要删除生产数据"},
            {"role": "assistant", "content": "会保持不变。"},
            {"role": "user", "content": "对，就这样"},
        ],
    }
    features = classify_task(payload, router_config)
    assert features.risk == "low"
    assert features.destructive is False


def test_read_only_and_dry_run_intents_are_not_inherited_as_high_risk(router_config):
    for prior_intent in (
        "Review only: rotate the production secret",
        "Dry run the production database migration",
        "只分析生产支付数据删除，不要执行",
        "只解释 git reset --hard 为什么危险",
    ):
        payload = {
            "model": "auto",
            "input": [
                {"role": "user", "content": prior_intent},
                {"role": "assistant", "content": "Read-only explanation complete."},
                {"role": "user", "content": "continue"},
            ],
        }
        features = classify_task(payload, router_config)
        assert features.risk == "low", prior_intent
        assert features.destructive is False, prior_intent


def test_plain_historical_risk_keywords_are_not_treated_as_actionable_intent(router_config):
    payload = {
        "model": "auto",
        "input": [
            {"role": "user", "content": "The release article mentions production payment and secret systems"},
            {"role": "assistant", "content": "Noted."},
            {"role": "user", "content": "continue"},
        ],
    }
    features = classify_task(payload, router_config)
    assert features.risk == "low"
    assert features.destructive is False


def test_conversation_risk_inheritance_has_a_bounded_item_window(router_config):
    payload = {
        "model": "auto",
        "input": [
            {"role": "user", "content": "Run git reset --hard HEAD~1"},
            *[
                {"role": "assistant", "content": f"Unrelated status update {index}"}
                for index in range(8)
            ],
            {"role": "user", "content": "go ahead"},
        ],
    }
    features = classify_task(payload, router_config)
    assert features.risk == "low"
    assert features.destructive is False


def test_new_normal_user_intent_stops_older_high_risk_inheritance(router_config):
    payload = {
        "model": "auto",
        "input": [
            {"role": "user", "content": "Delete the production payment database"},
            {"role": "assistant", "content": "I cannot do that without confirmation."},
            {"role": "user", "content": "Summarize the public release notes"},
            {"role": "assistant", "content": "The summary is ready."},
            {"role": "user", "content": "continue"},
        ],
    }
    features = classify_task(payload, router_config)
    assert features.risk == "low"
    assert features.destructive is False


def test_assistant_text_never_creates_inherited_destructive_intent(router_config):
    payload = {
        "model": "auto",
        "input": [
            {"role": "user", "content": "Rotate the production secret"},
            {
                "role": "assistant",
                "content": "I refuse. Do not run git reset --hard or DROP DATABASE production.",
            },
            {"role": "user", "content": "go ahead"},
        ],
    }
    features = classify_task(payload, router_config)
    assert features.risk == "high"
    assert features.destructive is False


def test_active_destructive_tool_arguments_keep_existing_safety_protection(router_config):
    payload = {
        "model": "auto",
        "input": [
            {"role": "user", "content": "Check the current state"},
                {
                    "type": "function_call",
                    "name": "shell",
                    "arguments": {"command": "git reset --hard HEAD~1"},
                },
            {"role": "user", "content": "show the result"},
        ],
    }
    features = classify_task(payload, router_config)
    assert features.risk == "high"
    assert features.destructive is True


def test_contract_large_tool_catalog_without_agentic_wording_stays_fast(router_config):
    payload = {
        "model": "auto",
        "input": "Summarize the release notes",
        "tools": [{"type": "function", "name": f"tool_{index}"} for index in range(100)],
    }
    features = classify_task(payload, router_config)
    decision = decide_route(features, router_config)
    assert features.tool_count == 100
    assert features.agentic is False
    assert decision.route_tier == RouteTier.FAST


def test_safety_invariant_project_rule_cannot_lower_high_risk_floor(router_config):
    config = router_config.model_copy(deep=True)
    config.projects["safety-floor-test"] = ProjectConfig(
        rules={TaskType.SUMMARY.value: RouteTier.FAST}
    )
    payload = {
        "model": "auto",
        "input": "Summarize the production payment authentication incident",
        "metadata": {"layman_project_id": "safety-floor-test"},
    }
    features = classify_task(payload, config)
    decision = decide_route(features, config, payload["metadata"])
    assert features.risk == "high"
    assert decision.route_tier == RouteTier.DEEP
    assert decision.route_reason[:2] == [
        "project rule: summary",
        "high-risk safety floor overrides lower route",
    ]


def test_contract_explicit_model_passthrough_survives_high_risk_input(router_config):
    payload = {
        "model": "custom-model",
        "input": "Run git reset --hard HEAD~1 against the production repository",
        "reasoning": {"effort": "low"},
    }
    features = classify_task(payload, router_config)
    decision = explicit_model_decision(payload, router_config, features)
    assert features.risk == "high"
    assert decision.automatic is False
    assert apply_route(payload, decision) == payload
    assert fallback_decision(decision, router_config) is None


def test_contract_availability_fallback_escalates_bound_model_and_effort_together(router_config):
    initial = decide_route(
        classify_task({"model": "auto", "input": "Summarize this note"}, router_config),
        router_config,
    )
    fallback = fallback_decision(initial, router_config)
    assert initial.route_tier == RouteTier.FAST
    assert initial.selected_model == "gpt-6-luna"
    assert initial.reasoning_effort == "low"
    assert fallback is not None
    assert fallback.route_tier == RouteTier.BALANCED
    assert fallback.selected_model == "gpt-6.1-sol"
    assert fallback.reasoning_effort == "medium"


def test_route_decision_exposes_uncalibrated_heuristic_structure(router_config):
    features = classify_task({"model": "auto", "input": "Summarize this note"}, router_config)
    decision = decide_route(features, router_config)
    dumped = decision.model_dump(mode="json")
    assert dumped["task_type"] == "summary"
    assert dumped["risk"] == "low"
    assert dumped["complexity"] == "low"
    assert dumped["selected_model"] == "gpt-6-luna"
    assert dumped["reasoning_effort"] == "low"
    assert dumped["route_tier"] == "fast"
    assert dumped["policy_version"]
    assert dumped["objective"]
    assert dumped["model_reason"]
    assert dumped["effort_reason"]
    assert dumped["calibration_state"] == "heuristic_uncalibrated"
    assert dumped["router_compute_ms"] == 0
    assert "confidence" not in dumped
