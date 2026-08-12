from __future__ import annotations

from copy import deepcopy
from typing import Any

from .models import RouteDecision, RouterConfig, RouteTier, TaskFeatures, TaskType


FAST_TASKS = {
    TaskType.SUMMARY,
    TaskType.REWRITE,
    TaskType.TRANSLATION,
    TaskType.CLASSIFICATION,
    TaskType.EXTRACTION,
}
DEEP_TASKS = {TaskType.DEBUGGING, TaskType.ARCHITECTURE, TaskType.SECURITY, TaskType.MATH}


def decide_route(features: TaskFeatures, config: RouterConfig, metadata: dict[str, Any] | None = None) -> RouteDecision:
    metadata = metadata or {}
    project = config.projects.get(features.project_id) or config.projects.get("default")
    reasons: list[str] = []

    requested = metadata.get("layman_route")
    if requested in {item.value for item in RouteTier}:
        tier = RouteTier(requested)
        reasons.append(f"request override: {tier.value}")
    elif project and features.task_type.value in project.rules:
        tier = project.rules[features.task_type.value]
        reasons.append(f"project rule: {features.task_type.value}")
    elif features.risk == "high":
        tier = RouteTier.DEEP
        reasons.append("high-risk task")
    elif features.task_type in DEEP_TASKS:
        tier = RouteTier.DEEP
        reasons.append(f"{features.task_type.value} task")
    elif features.task_type in FAST_TASKS and not features.agentic:
        tier = RouteTier.FAST
        reasons.append(f"routine {features.task_type.value} task")
    else:
        tier = RouteTier.BALANCED
        reasons.append(f"{features.task_type.value} task")

    if features.risk == "high" and tier != RouteTier.DEEP:
        tier = RouteTier.DEEP
        reasons.append("high-risk safety floor overrides lower route")
    if features.agentic and tier == RouteTier.FAST:
        tier = RouteTier.BALANCED
        reasons.append("tool-heavy request requires balanced minimum")
    if features.complexity == "high" and tier == RouteTier.FAST:
        tier = RouteTier.BALANCED
        reasons.append("high input complexity")
    if features.quality == "production" and features.risk != "low" and tier != RouteTier.DEEP:
        tier = RouteTier.DEEP
        reasons.append("production quality with elevated risk")
    if features.budget == "low" and tier == RouteTier.BALANCED and features.risk == "low" and not features.agentic:
        tier = RouteTier.FAST
        reasons.append("low budget and low risk")

    tier_config = config.tiers[tier]
    return RouteDecision(
        selected_model=tier_config.model,
        reasoning_effort=tier_config.reasoning_effort,
        max_output_tokens=tier_config.max_output_tokens,
        route_tier=tier,
        route_reason=reasons,
    )


def explicit_model_decision(payload: dict[str, Any], config: RouterConfig) -> RouteDecision:
    model = str(payload["model"])
    matching = next(((tier, spec) for tier, spec in config.tiers.items() if spec.model == model), None)
    if matching:
        tier, spec = matching
        effort = str((payload.get("reasoning") or {}).get("effort") or spec.reasoning_effort)
        max_tokens = int(payload.get("max_output_tokens") or spec.max_output_tokens)
    else:
        tier, spec = RouteTier.BALANCED, config.tiers[RouteTier.BALANCED]
        effort = str((payload.get("reasoning") or {}).get("effort") or "unchanged")
        max_tokens = int(payload.get("max_output_tokens") or spec.max_output_tokens)
    return RouteDecision(
        selected_model=model,
        reasoning_effort=effort,
        max_output_tokens=max_tokens,
        route_tier=tier,
        route_reason=["explicit model passthrough"],
        automatic=False,
    )


def apply_route(payload: dict[str, Any], decision: RouteDecision) -> dict[str, Any]:
    routed = deepcopy(payload)
    if not decision.automatic:
        return routed
    routed["model"] = decision.selected_model
    reasoning = routed.get("reasoning") if isinstance(routed.get("reasoning"), dict) else {}
    reasoning = deepcopy(reasoning)
    reasoning["effort"] = decision.reasoning_effort
    routed["reasoning"] = reasoning
    requested_limit = routed.get("max_output_tokens")
    routed["max_output_tokens"] = min(int(requested_limit), decision.max_output_tokens) if requested_limit else decision.max_output_tokens
    return routed


def fallback_decision(current: RouteDecision, config: RouterConfig) -> RouteDecision | None:
    if not current.automatic or current.route_tier == RouteTier.DEEP:
        return None
    next_tier = RouteTier.BALANCED if current.route_tier == RouteTier.FAST else RouteTier.DEEP
    spec = config.tiers[next_tier]
    return RouteDecision(
        selected_model=spec.model,
        reasoning_effort=spec.reasoning_effort,
        max_output_tokens=spec.max_output_tokens,
        route_tier=next_tier,
        route_reason=[*current.route_reason, f"single fallback to {next_tier.value}"],
        automatic=True,
    )
