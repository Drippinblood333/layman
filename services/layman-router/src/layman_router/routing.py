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
    TaskType.DOCUMENTATION,
}
DEEP_TASKS = {TaskType.DEBUGGING, TaskType.ARCHITECTURE, TaskType.SECURITY, TaskType.MATH}
ROUTING_POLICY_VERSION = "heuristic-v1"


def _objective(features: TaskFeatures) -> str:
    if features.risk == "high":
        return "safety"
    if features.quality == "production":
        return "quality"
    if features.budget == "low" or features.quality == "economy":
        return "economy"
    return "balanced"


def structured_decision(decision: RouteDecision) -> dict[str, Any]:
    return {
        "task_type": decision.task_type.value,
        "risk": decision.risk,
        "complexity": decision.complexity,
        "selected_model": decision.selected_model,
        "reasoning_effort": decision.reasoning_effort,
        "output_verbosity": decision.output_verbosity,
        "route_tier": decision.route_tier.value,
        "policy_version": decision.policy_version,
        "objective": decision.objective,
        "model_reason": decision.model_reason,
        "effort_reason": decision.effort_reason,
        "calibration_state": decision.calibration_state,
        "router_compute_ms": decision.router_compute_ms,
    }


def router_overhead(decision: RouteDecision) -> dict[str, float]:
    return {
        "feature_extraction_ms": decision.feature_extraction_ms,
        "policy_decision_ms": decision.policy_decision_ms,
        "router_compute_ms": decision.router_compute_ms,
        "total_routing_preflight_ms": decision.total_routing_preflight_ms,
    }


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
        output_verbosity=tier_config.verbosity,
        max_output_tokens=tier_config.max_output_tokens,
        route_tier=tier,
        route_reason=reasons,
        task_type=features.task_type,
        risk=features.risk,
        complexity=features.complexity,
        policy_version=ROUTING_POLICY_VERSION,
        objective=_objective(features),
        model_reason=f"{tier.value} preset selected by heuristic policy",
        effort_reason=f"{tier.value} preset binds reasoning effort to {tier_config.reasoning_effort}",
    )


def explicit_model_decision(
    payload: dict[str, Any],
    config: RouterConfig,
    features: TaskFeatures | None = None,
) -> RouteDecision:
    model = str(payload["model"])
    matching = next(((tier, spec) for tier, spec in config.tiers.items() if spec.model == model), None)
    if matching:
        tier, spec = matching
        effort = str((payload.get("reasoning") or {}).get("effort") or spec.reasoning_effort)
        verbosity = str((payload.get("text") or {}).get("verbosity") or spec.verbosity)
        max_tokens = int(payload.get("max_output_tokens") or spec.max_output_tokens)
    else:
        tier, spec = RouteTier.BALANCED, config.tiers[RouteTier.BALANCED]
        effort = str((payload.get("reasoning") or {}).get("effort") or "unchanged")
        verbosity = str((payload.get("text") or {}).get("verbosity") or "unchanged")
        max_tokens = int(payload.get("max_output_tokens") or spec.max_output_tokens)
    return RouteDecision(
        selected_model=model,
        reasoning_effort=effort,
        output_verbosity=verbosity,
        max_output_tokens=max_tokens,
        route_tier=tier,
        route_reason=["explicit model passthrough"],
        automatic=False,
        task_type=features.task_type if features else TaskType.GENERAL,
        risk=features.risk if features else "low",
        complexity=features.complexity if features else "low",
        policy_version=ROUTING_POLICY_VERSION,
        objective="explicit_passthrough",
        model_reason="caller supplied an explicit model",
        effort_reason=(
            "caller supplied explicit reasoning effort"
            if isinstance(payload.get("reasoning"), dict) and payload["reasoning"].get("effort")
            else "explicit passthrough preserves caller payload"
        ),
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
    text = routed.get("text") if isinstance(routed.get("text"), dict) else {}
    text = deepcopy(text)
    text["verbosity"] = decision.output_verbosity
    routed["text"] = text
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
        output_verbosity=spec.verbosity,
        max_output_tokens=spec.max_output_tokens,
        route_tier=next_tier,
        route_reason=[*current.route_reason, f"single fallback to {next_tier.value}"],
        automatic=True,
        task_type=current.task_type,
        risk=current.risk,
        complexity=current.complexity,
        policy_version=current.policy_version,
        objective=current.objective,
        model_reason=f"availability fallback to {next_tier.value} preset model",
        effort_reason=f"{next_tier.value} fallback preset binds reasoning effort to {spec.reasoning_effort}",
        calibration_state=current.calibration_state,
        router_compute_ms=current.router_compute_ms,
        feature_extraction_ms=current.feature_extraction_ms,
        policy_decision_ms=current.policy_decision_ms,
        total_routing_preflight_ms=current.total_routing_preflight_ms,
    )
