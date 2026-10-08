#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from layman_router.classify import classify_task
from layman_router.config import load_config
from layman_router.routing import decide_route

ROOT = Path(__file__).resolve().parent
ORDER = {"fast": 0, "balanced": 1, "deep": 2}


def main() -> int:
    config = load_config()
    cases = [json.loads(line) for line in (ROOT / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line]
    errors, by_category, reasons = [], defaultdict(Counter), Counter()
    started = time.perf_counter()
    loops = 50
    for _ in range(loops):
        for case in cases:
            payload = case.get("request") or {"model": "auto", "input": case["input"]}
            features = classify_task(payload, config)
            decision = decide_route(features, config, payload.get("metadata"))
            if _ == 0:
                expected, actual = case["expected_tier"], decision.route_tier.value
                by_category[case["category"]][f"{expected}->{actual}"] += 1
                reasons.update(decision.route_reason)
                if expected != actual or case["expected_task_type"] != features.task_type.value or case.get("expected_risk") != features.risk:
                    errors.append({
                        "id": case["id"], "category": case["category"],
                        "expected_tier": expected, "actual_tier": actual,
                        "severity": "under-route" if ORDER[actual] < ORDER[expected] else "over-route" if ORDER[actual] > ORDER[expected] else "classification",
                        "expected_task_type": case["expected_task_type"], "actual_task_type": features.task_type.value,
                        "expected_risk": case.get("expected_risk"), "actual_risk": features.risk,
                        "route_reason": decision.route_reason,
                    })
    elapsed = time.perf_counter() - started
    report = {
        "cases": len(cases), "iterations": loops * len(cases),
        "elapsed_seconds": round(elapsed, 4), "routes_per_second": round(loops * len(cases) / elapsed),
        "misjudgments": len(errors), "under_routes": sum(e["severity"] == "under-route" for e in errors),
        "over_routes": sum(e["severity"] == "over-route" for e in errors),
        "by_category": {key: dict(value) for key, value in by_category.items()},
        "top_route_reasons": reasons.most_common(12), "errors": errors,
    }
    output = ROOT / "results" / "routing-analysis.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "errors"}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
