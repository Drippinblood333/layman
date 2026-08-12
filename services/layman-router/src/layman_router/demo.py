from __future__ import annotations

import hashlib

from .models import RouterConfig, RouteTier, UsageRecord
from .telemetry import UsageStore


def seed_demo(store: UsageStore, config: RouterConfig, count: int = 36) -> None:
    tiers = [RouteTier.FAST] * 5 + [RouteTier.BALANCED] * 3 + [RouteTier.DEEP] * 2
    tasks = ["summary", "rewrite", "extraction", "code_explanation", "normal_coding", "debugging", "architecture"]
    for index in range(count):
        tier = tiers[index % len(tiers)]
        spec = config.tiers[tier]
        input_tokens = 700 + (index * 137) % 4200
        output_tokens = 90 + (index * 43) % 700
        input_cost = input_tokens * spec.pricing.input_per_million / 1_000_000
        output_cost = output_tokens * spec.pricing.output_per_million / 1_000_000
        deep = config.tiers[RouteTier.DEEP].pricing
        baseline = (input_tokens * deep.input_per_million + output_tokens * deep.output_per_million) / 1_000_000
        error = "synthetic_timeout" if index in {17, 31} else None
        store.add(UsageRecord(
            request_id=f"demo-{index:04d}", project_id="demo-project",
            prompt_hash=hashlib.sha256(f"synthetic-demo-{index}".encode()).hexdigest(),
            task_type=tasks[index % len(tasks)], complexity=("high" if tier == RouteTier.DEEP else "medium" if tier == RouteTier.BALANCED else "low"),
            risk=("high" if tier == RouteTier.DEEP else "low"), route_tier=tier.value,
            selected_model=spec.model, reasoning_effort=spec.reasoning_effort,
            route_reason=["synthetic demo record"], input_tokens=input_tokens,
            cached_tokens=input_tokens // 5, output_tokens=output_tokens,
            reasoning_tokens=output_tokens // 4, latency_ms=380 + (index * 211) % 4200,
            estimated_cost_usd=round(input_cost + output_cost, 9),
            estimated_always_deep_cost_usd=round(baseline, 9),
            fallback_used=index in {11, 28}, validator_passed=error is None,
            error_category=error, metadata={"synthetic_demo": True},
        ))
