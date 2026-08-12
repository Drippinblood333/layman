#!/usr/bin/env python3
"""Budget-capped, resumable real-API benchmark for auto versus always-deep."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx

from layman_router.config import load_config
from layman_router.models import RouteTier
from layman_router.telemetry import estimate_cost, extract_usage, price_for_model
from layman_router.validation import output_text

ROOT = Path(__file__).resolve().parent
JUDGE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["answer_a", "answer_b", "winner", "reason"],
    "properties": {
        "answer_a": {"type": "number", "minimum": 1, "maximum": 5},
        "answer_b": {"type": "number", "minimum": 1, "maximum": 5},
        "winner": {"type": "string", "enum": ["a", "b", "tie"]},
        "reason": {"type": "string", "maxLength": 300},
    },
}


class BenchmarkRequestError(RuntimeError):
    def __init__(self, status_code: int):
        super().__init__(f"upstream request failed with HTTP {status_code}; response body was not retained")
        self.status_code = status_code


def cases(per_category: int) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in (ROOT / "cases.jsonl").read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        groups[case["category"]].append(case)
    selected = []
    for category in sorted(groups):
        pool = groups[category]
        # Spread samples across easy, boundary, and risk variants instead of taking the first N.
        positions = [round(i * (len(pool) - 1) / max(per_category - 1, 1)) for i in range(per_category)]
        selected.extend(pool[position] for position in dict.fromkeys(positions))
    return selected


def request(client: httpx.Client, payload: dict[str, Any], config: Any) -> dict[str, Any]:
    started = time.perf_counter()
    response = client.post("/v1/responses", json=payload)
    if not response.is_success:
        raise BenchmarkRequestError(response.status_code)
    body = response.json()
    model = response.headers.get("x-layman-selected-model") or body.get("model") or payload["model"]
    usage = extract_usage(body)
    return {
        "model": model, "route_tier": response.headers.get("x-layman-route-tier"),
        "fallback_used": response.headers.get("x-layman-fallback-used") == "true",
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "usage": usage, "cost_usd": estimate_cost(usage, price_for_model(config, model) or config.tiers[RouteTier.DEEP].pricing),
        "status": body.get("status"), "text": output_text(body),
    }


def judge(client: httpx.Client, case: dict[str, Any], auto: dict[str, Any], deep: dict[str, Any], config: Any, max_tokens: int) -> dict[str, Any]:
    auto_is_a = int(hashlib.sha256(case["id"].encode()).hexdigest(), 16) % 2 == 0
    a, b = (auto, deep) if auto_is_a else (deep, auto)
    prompt = (
        "You are a strict blind evaluator. Score each answer from 1 to 5 for correctness, completeness, "
        "instruction following, and useful concision. Do not prefer verbosity.\n\n"
        f"TASK:\n{case['input']}\n\nANSWER A:\n{a['text']}\n\nANSWER B:\n{b['text']}"
    )
    result = request(client, {
        "model": config.tiers[RouteTier.DEEP].model, "input": prompt, "store": False,
        "reasoning": {"effort": "low"}, "max_output_tokens": max_tokens,
        "text": {"format": {"type": "json_schema", "name": "layman_benchmark_judge", "strict": True, "schema": JUDGE_SCHEMA}},
    }, config)
    verdict = json.loads(result["text"])
    return {
        "auto_score": verdict["answer_a"] if auto_is_a else verdict["answer_b"],
        "deep_score": verdict["answer_b"] if auto_is_a else verdict["answer_a"],
        "winner": ("auto" if verdict["winner"] == ("a" if auto_is_a else "b") else "deep" if verdict["winner"] in {"a", "b"} else "tie"),
        "reason": verdict["reason"], "cost_usd": result["cost_usd"], "model": result["model"],
    }


def case_cost_ceiling(case: dict[str, Any], config: Any, output_tokens: int, judge_tokens: int, with_judge: bool) -> float:
    deep = config.tiers[RouteTier.DEEP].pricing
    input_tokens = max(32, len(case["input"]) // 2)
    pair = 2 * (input_tokens * deep.input_per_million + output_tokens * deep.output_per_million) / 1_000_000
    if not with_judge:
        return pair
    judge_input = input_tokens + output_tokens * 2 + 160
    return pair + (judge_input * deep.input_per_million + judge_tokens * deep.output_per_million) / 1_000_000


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--per-category", type=int, default=2)
    parser.add_argument("--max-output-tokens", type=int, default=384)
    parser.add_argument("--judge-output-tokens", type=int, default=256)
    parser.add_argument("--max-cost-usd", type=float, default=1.0)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "real-benchmark.jsonl")
    parser.add_argument("--no-judge", action="store_true")
    args = parser.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set")
    if args.per_category < 1 or args.max_cost_usd <= 0:
        raise SystemExit("per-category and max-cost-usd must be positive")

    config = load_config()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    completed = {}
    if args.output.exists():
        completed = {item["id"]: item for item in (json.loads(line) for line in args.output.read_text(encoding="utf-8").splitlines() if line)}
    spent = sum(item["auto"]["cost_usd"] + item["deep"]["cost_usd"] + (item.get("judge") or {}).get("cost_usd", 0) for item in completed.values())
    failure_path = args.output.with_suffix(".failure.json")
    failed = False
    headers = {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
    with httpx.Client(base_url=args.base_url, headers=headers, timeout=300) as client:
        health = client.get("/healthz")
        health.raise_for_status()
        for case in cases(args.per_category):
            existing = completed.get(case["id"])
            if existing and (args.no_judge or existing.get("judge")):
                continue
            if existing:
                try:
                    existing["judge"] = judge(client, case, existing["auto"], existing["deep"], config, args.judge_output_tokens)
                except BenchmarkRequestError as exc:
                    failure_path.write_text(json.dumps({"id": case["id"], "phase": "judge", "status_code": exc.status_code, "error_category": "authentication" if exc.status_code == 401 else "upstream_http_error"}, indent=2), encoding="utf-8")
                    failed = True
                    break
                with args.output.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(existing, ensure_ascii=False) + "\n")
                spent += existing["judge"]["cost_usd"]
                continue
            ceiling = case_cost_ceiling(case, config, args.max_output_tokens, args.judge_output_tokens, not args.no_judge)
            if spent + ceiling > args.max_cost_usd:
                print(f"budget stop before {case['id']}: ${spent:.6f} spent, ${ceiling:.6f} conservative next-case ceiling", flush=True)
                break
            base = case.get("request") or {"model": "auto", "input": case["input"]}
            common = {**base, "store": False, "max_output_tokens": min(args.max_output_tokens, int(base.get("max_output_tokens") or args.max_output_tokens))}
            try:
                auto = request(client, {**common, "model": "auto"}, config)
                deep = request(client, {**common, "model": config.tiers[RouteTier.DEEP].model}, config)
            except BenchmarkRequestError as exc:
                failure = {"id": case["id"], "status_code": exc.status_code, "error_category": "authentication" if exc.status_code == 401 else "upstream_http_error"}
                failure_path.write_text(json.dumps(failure, indent=2), encoding="utf-8")
                print(str(exc), flush=True)
                failed = True
                break
            result = {"id": case["id"], "category": case["category"], "expected_tier": case["expected_tier"], "auto": auto, "deep": deep}
            if not args.no_judge:
                try:
                    result["judge"] = judge(client, case, auto, deep, config, args.judge_output_tokens)
                except BenchmarkRequestError as exc:
                    result["judge_error"] = {"status_code": exc.status_code, "error_category": "authentication" if exc.status_code == 401 else "upstream_http_error"}
                    failure_path.write_text(json.dumps({"id": case["id"], "phase": "judge", **result["judge_error"]}, indent=2), encoding="utf-8")
                    failed = True
            with args.output.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
            completed[case["id"]] = result
            spent += auto["cost_usd"] + deep["cost_usd"] + (result.get("judge") or {}).get("cost_usd", 0)
            print(f"{case['id']}: ${spent:.6f} cumulative", flush=True)
            if failed:
                break

    rows = list(completed.values())
    auto_cost = sum(row["auto"]["cost_usd"] for row in rows)
    deep_cost = sum(row["deep"]["cost_usd"] for row in rows)
    judged = [row for row in rows if row.get("judge")]
    summary = {
        "cases": len(rows), "categories": sorted({row["category"] for row in rows}),
        "auto_cost_usd": round(auto_cost, 6), "always_deep_cost_usd": round(deep_cost, 6),
        "judge_cost_usd": round(sum(row["judge"]["cost_usd"] for row in judged), 6),
        "total_benchmark_cost_usd": round(spent, 6),
        "measured_savings_percent": round((deep_cost - auto_cost) / deep_cost * 100, 2) if deep_cost else None,
        "auto_quality_mean": round(statistics.mean(row["judge"]["auto_score"] for row in judged), 3) if judged else None,
        "deep_quality_mean": round(statistics.mean(row["judge"]["deep_score"] for row in judged), 3) if judged else None,
        "quality_delta": round(statistics.mean(row["judge"]["auto_score"] - row["judge"]["deep_score"] for row in judged), 3) if judged else None,
        "fallback_rate": round(sum(row["auto"]["fallback_used"] for row in rows) / len(rows), 4) if rows else None,
        "release_gate_note": "A calibration run is real evidence but does not satisfy the 300-case release gate unless all 300 cases are present and human scores are completed.",
    }
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if not failed and failure_path.exists():
        failure_path.unlink()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
