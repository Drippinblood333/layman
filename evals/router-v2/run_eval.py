#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

from layman_router.classify import classify_task
from layman_router.config import load_config
from layman_router.models import RouteTier
from layman_router.routing import decide_route
from layman_router.telemetry import estimate_cost, extract_usage
from layman_router.validation import output_text


ROOT = Path(__file__).resolve().parent


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in (ROOT / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def static_eval() -> int:
    config = load_config()
    failures = []
    counts = Counter()
    confusion = Counter()
    for case in load_cases():
        payload = case.get("request") or {"model": "auto", "input": case["input"]}
        features = classify_task(payload, config)
        decision = decide_route(features, config, payload.get("metadata"))
        counts[decision.route_tier.value] += 1
        confusion[(case["expected_tier"], decision.route_tier.value)] += 1
        if features.task_type.value != case["expected_task_type"] or decision.route_tier.value != case["expected_tier"] or features.risk != case.get("expected_risk", features.risk):
            failures.append({
                "id": case["id"],
                "task_type": features.task_type.value,
                "tier": decision.route_tier.value,
                "expected_task_type": case["expected_task_type"],
                "expected_tier": case["expected_tier"],
                "risk": features.risk,
                "expected_risk": case.get("expected_risk"),
                "route_reason": decision.route_reason,
            })
        if features.risk == "high" and decision.route_tier != RouteTier.DEEP:
            failures.append({"id": case["id"], "error": "high-risk task routed below deep"})
    print(json.dumps({"total": len(load_cases()), "tiers": counts, "confusion": {f"{a}->{b}": n for (a, b), n in confusion.items()}, "failures": failures[:20]}, indent=2, ensure_ascii=False))
    return 1 if failures else 0


def live_eval(base_url: str, limit: int | None, output: Path) -> int:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENAI_API_KEY for live eval. Static eval never requires it.")
    config = load_config()
    cases = load_cases()[:limit]
    results = []
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(base_url=base_url, headers=headers, timeout=180) as client:
        for case in cases:
            pair = {"id": case["id"], "category": case["category"]}
            for label, model in (("auto", "auto"), ("deep", config.tiers[RouteTier.DEEP].model)):
                response = client.post("/v1/responses", json={
                    "model": model,
                    "input": case["input"],
                    "store": False,
                    "metadata": {"layman_project_id": "router-v2-eval"},
                })
                response.raise_for_status()
                body = response.json()
                usage = extract_usage(body)
                selected = body.get("model", model)
                pricing = next((spec.pricing for spec in config.tiers.values() if spec.model == selected), config.tiers[RouteTier.DEEP].pricing)
                pair[label] = {
                    "model": selected,
                    "usage": usage,
                    "cost_usd": estimate_cost(usage, pricing),
                    "validator_passed": body.get("status") == "completed" and bool(body.get("output")),
                    "output_text": output_text(body),
                    "route_tier": response.headers.get("x-layman-route-tier"),
                    "fallback_used": response.headers.get("x-layman-fallback-used") == "true",
                    "human_score": None,
                }
            results.append(pair)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in results), encoding="utf-8")
    auto_cost = sum(item["auto"]["cost_usd"] for item in results)
    deep_cost = sum(item["deep"]["cost_usd"] for item in results)
    measured = ((deep_cost - auto_cost) / deep_cost * 100) if deep_cost else 0
    print(json.dumps({"cases": len(results), "auto_cost_usd": auto_cost, "deep_cost_usd": deep_cost, "measured_savings_percent": measured}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "live-results.jsonl")
    args = parser.parse_args()
    return live_eval(args.base_url, args.limit, args.output) if args.live else static_eval()


if __name__ == "__main__":
    raise SystemExit(main())
