#!/usr/bin/env python3
"""Budget-accounted, resumable real-API calibration for auto versus always-deep."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

import httpx

from layman_router.config import (
    load_config,
    routing_config_sha256,
    upstream_identity_sha256,
)
from layman_router.models import RouteTier
from layman_router.telemetry import estimate_cost, extract_usage, price_for_model
from layman_router.validation import output_text

ROOT = Path(__file__).resolve().parent
BENCHMARK_PROTOCOL_VERSION = 3
SERVICE_TIER = "default"
JUDGE_INSTRUCTIONS = (
    "You are a strict blind evaluator. Score each answer from 1 to 5 for correctness, "
    "completeness, instruction following, and useful concision. Do not prefer verbosity."
)
JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
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
        super().__init__(
            f"upstream request failed with HTTP {status_code}; response body was not retained"
        )
        self.status_code = status_code


def cases(per_category: int) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in (ROOT / "cases.jsonl").read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        groups[case["category"]].append(case)
    selected = []
    for category in sorted(groups):
        pool = groups[category]
        positions = [
            round(i * (len(pool) - 1) / max(per_category - 1, 1))
            for i in range(per_category)
        ]
        selected.extend(pool[position] for position in dict.fromkeys(positions))
    return selected


def unsupported_live_cases(selected_cases: list[dict[str, Any]]) -> dict[str, list[str]]:
    unsupported = {"previous_response_id": [], "tools": []}
    for case in selected_cases:
        request_payload = case.get("request") or {}
        for field in unsupported:
            if request_payload.get(field):
                unsupported[field].append(str(case["id"]))
    return {field: ids for field, ids in unsupported.items() if ids}


def benchmark_fingerprint(
    selected_cases: list[dict[str, Any]],
    config: Any,
    *,
    max_output_tokens: int,
    judge_output_tokens: int,
    with_judge: bool,
    base_url: str,
    health: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    payload = {
        "protocol_version": BENCHMARK_PROTOCOL_VERSION,
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "cases": selected_cases,
        "router_config": config.model_dump(mode="json"),
        "router_health": {
            "price_version": health.get("price_version"),
            "tiers": health.get("tiers"),
            "routing_config_sha256": health.get("routing_config_sha256"),
            "upstream_identity_sha256": health.get("upstream_identity_sha256"),
        },
        "base_url": base_url.rstrip("/"),
        "max_output_tokens": max_output_tokens,
        "judge_output_tokens": judge_output_tokens,
        "with_judge": with_judge,
        "service_tier": SERVICE_TIER,
        "judge_instructions": JUDGE_INSTRUCTIONS,
        "judge_schema": JUDGE_SCHEMA,
        "blind_ordering": "sha256(case_id) parity; even means auto is answer_a",
    }
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return fingerprint, payload


def validate_router_health(health: Mapping[str, Any], config: Any) -> None:
    if config.upstream_base_url.rstrip("/").lower() != "https://api.openai.com/v1":
        raise RuntimeError("real-API benchmark requires the official OpenAI upstream")
    expected_tiers = {tier.value: spec.model for tier, spec in config.tiers.items()}
    if health.get("price_version") != config.price_version:
        raise RuntimeError("router health price_version differs from the local benchmark config")
    if health.get("tiers") != expected_tiers:
        raise RuntimeError("router health tiers differ from the local benchmark config")
    if health.get("routing_config_sha256") != routing_config_sha256(config):
        raise RuntimeError("router routing configuration differs from the local benchmark config")
    if health.get("upstream_identity_sha256") != upstream_identity_sha256(config):
        raise RuntimeError("router upstream differs from the local benchmark config")


def request(client: httpx.Client, payload: dict[str, Any], config: Any) -> dict[str, Any]:
    started = time.perf_counter()
    response = client.post("/v1/responses", json=payload)
    if not response.is_success:
        raise BenchmarkRequestError(response.status_code)
    body = response.json()
    model = (
        response.headers.get("x-layman-selected-model")
        or body.get("model")
        or payload["model"]
    )
    usage = extract_usage(body)
    fallback_used = response.headers.get("x-layman-fallback-used") == "true"
    actual_service_tier = body.get("service_tier")
    validator_header = response.headers.get("x-layman-validator-passed")
    validator_passed = (
        validator_header == "true" if validator_header in {"true", "false"} else None
    )
    estimate = estimate_cost(
        usage,
        price_for_model(config, model) or config.tiers[RouteTier.DEEP].pricing,
    )
    return {
        "request_id": response.headers.get("x-layman-request-id"),
        "model": model,
        "route_tier": response.headers.get("x-layman-route-tier"),
        "fallback_used": fallback_used,
        "validator_passed": validator_passed,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "usage": usage,
        "estimated_cost_from_measured_usage_usd": estimate,
        "requested_service_tier": SERVICE_TIER,
        "response_service_tier": actual_service_tier,
        "cost_comparison_eligible": (
            not fallback_used
            and validator_passed is True
            and actual_service_tier == SERVICE_TIER
            and body.get("status") == "completed"
        ),
        "status": body.get("status"),
        "text": output_text(body),
    }


def judge_payload(
    case: dict[str, Any],
    auto: dict[str, Any],
    deep: dict[str, Any],
    config: Any,
    max_tokens: int,
) -> tuple[dict[str, Any], bool]:
    auto_is_a = int(hashlib.sha256(case["id"].encode()).hexdigest(), 16) % 2 == 0
    a, b = (auto, deep) if auto_is_a else (deep, auto)
    prompt = (
        f"{JUDGE_INSTRUCTIONS}\n\nTASK:\n{case['input']}\n\n"
        f"ANSWER A:\n{a['text']}\n\nANSWER B:\n{b['text']}"
    )
    return (
        {
            "model": config.tiers[RouteTier.DEEP].model,
            "input": prompt,
            "store": False,
            "service_tier": SERVICE_TIER,
            "reasoning": {"effort": "low"},
            "max_output_tokens": max_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "layman_benchmark_judge",
                    "strict": True,
                    "schema": JUDGE_SCHEMA,
                }
            },
        },
        auto_is_a,
    )


def judge_result(result: dict[str, Any], *, auto_is_a: bool) -> dict[str, Any]:
    verdict = json.loads(result["text"])
    return {
        "auto_score": verdict["answer_a"] if auto_is_a else verdict["answer_b"],
        "deep_score": verdict["answer_b"] if auto_is_a else verdict["answer_a"],
        "winner": (
            "auto"
            if verdict["winner"] == ("a" if auto_is_a else "b")
            else "deep"
            if verdict["winner"] in {"a", "b"}
            else "tie"
        ),
        "reason": verdict["reason"],
        "request": result,
    }


def request_cost_ceiling(
    payload: Mapping[str, Any], config: Any, *, attempt_multiplier: int = 1
) -> float:
    input_token_upper_bound = max(
        32,
        len(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ),
    )
    output_tokens = int(payload.get("max_output_tokens") or 0)
    usage = {
        "input_tokens": input_token_upper_bound,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
        "output_tokens": output_tokens,
        "reasoning_tokens": 0,
    }
    return round(
        estimate_cost(usage, config.tiers[RouteTier.DEEP].pricing) * attempt_multiplier,
        9,
    )


def append_event(path: Path, event: Mapping[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def load_events(path: Path, fingerprint: str) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, dict[str, Any]]]:
    completions: dict[tuple[str, str], dict[str, Any]] = {}
    reservations: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return completions, reservations
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        event = json.loads(line)
        if event.get("experiment_fingerprint") != fingerprint:
            continue
        if event.get("type") == "reservation":
            reservations[str(event["reservation_id"])] = event
        elif event.get("type") == "completion":
            reservation_id = str(event["reservation_id"])
            reservations.pop(reservation_id, None)
            completions[(str(event["case_id"]), str(event["arm"]))] = event
    return completions, reservations


def accounted_spend(
    completions: Mapping[tuple[str, str], Mapping[str, Any]],
    reservations: Mapping[str, Mapping[str, Any]],
) -> tuple[float, float, float]:
    completed = sum(float(event["accounted_cost_usd"]) for event in completions.values())
    unresolved = sum(float(event["ceiling_usd"]) for event in reservations.values())
    return completed, unresolved, completed + unresolved


def reserve_call(
    output: Path,
    *,
    fingerprint: str,
    case_id: str,
    arm: str,
    ceiling_usd: float,
    cap_accounted_spend: float,
    max_cost_usd: float,
) -> dict[str, Any] | None:
    if cap_accounted_spend + ceiling_usd > max_cost_usd:
        return None
    event = {
        "type": "reservation",
        "experiment_fingerprint": fingerprint,
        "reservation_id": uuid.uuid4().hex,
        "case_id": case_id,
        "arm": arm,
        "ceiling_usd": ceiling_usd,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    append_event(output, event)
    return event


def complete_call(
    output: Path,
    reservation: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    measured = float(result.get("estimated_cost_from_measured_usage_usd") or 0)
    eligible = bool(result.get("cost_comparison_eligible"))
    accounted = measured if eligible else float(reservation["ceiling_usd"])
    if accounted > float(reservation["ceiling_usd"]) + 1e-9:
        raise RuntimeError("measured price-table cost exceeded the reserved ceiling")
    event = {
        "type": "completion",
        "experiment_fingerprint": reservation["experiment_fingerprint"],
        "reservation_id": reservation["reservation_id"],
        "case_id": reservation["case_id"],
        "arm": reservation["arm"],
        "ceiling_usd": reservation["ceiling_usd"],
        "accounted_cost_usd": accounted,
        "result": result,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    append_event(output, event)
    return event


def failure_record(case_id: str, arm: str, exc: BenchmarkRequestError) -> dict[str, Any]:
    return {
        "id": case_id,
        "arm": arm,
        "status_code": exc.status_code,
        "error_category": "authentication"
        if exc.status_code == 401
        else "upstream_http_error",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--per-category", type=int, default=2)
    parser.add_argument("--max-output-tokens", type=int, default=384)
    parser.add_argument("--judge-output-tokens", type=int, default=256)
    parser.add_argument("--max-cost-usd", type=float, default=1.0)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results" / "real-benchmark.jsonl"
    )
    parser.add_argument("--no-judge", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if (
        args.per_category < 1
        or args.max_output_tokens < 1
        or args.judge_output_tokens < 1
        or not math.isfinite(args.max_cost_usd)
        or args.max_cost_usd <= 0
    ):
        raise SystemExit(
            "per-category, output limits, and a finite max-cost-usd must be positive"
        )

    selected_cases = cases(args.per_category)
    unsupported = unsupported_live_cases(selected_cases)
    if unsupported:
        raise SystemExit(
            "selected live cases require unsupported state/tool execution; no API call was made: "
            + json.dumps(unsupported, sort_keys=True)
        )
    if args.validate_only:
        print(json.dumps({"status": "supported", "cases": len(selected_cases)}))
        return 0
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set")

    config = load_config()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    failure_path = args.output.with_suffix(".failure.json")
    headers = {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
    failed = False

    with httpx.Client(base_url=args.base_url, headers=headers, timeout=300) as client:
        health_response = client.get("/healthz")
        health_response.raise_for_status()
        health = health_response.json()
        validate_router_health(health, config)
        fingerprint, fingerprint_payload = benchmark_fingerprint(
            selected_cases,
            config,
            max_output_tokens=args.max_output_tokens,
            judge_output_tokens=args.judge_output_tokens,
            with_judge=not args.no_judge,
            base_url=args.base_url,
            health=health,
        )
        manifest_path = args.output.with_suffix(".manifest.json")
        manifest_path.write_text(
            json.dumps(
                {
                    "experiment_fingerprint": fingerprint,
                    "definition": fingerprint_payload,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        completions, reservations = load_events(args.output, fingerprint)
        if reservations:
            _, unresolved, total = accounted_spend(completions, reservations)
            raise SystemExit(
                f"unresolved in-flight reservations account for ${unresolved:.6f} "
                f"(${total:.6f} total); review the WAL and use a new output path before more API calls"
            )

        for case in selected_cases:
            base = case.get("request") or {"model": "auto", "input": case["input"]}
            common = {
                **base,
                "store": False,
                "service_tier": SERVICE_TIER,
                "max_output_tokens": min(
                    args.max_output_tokens,
                    int(base.get("max_output_tokens") or args.max_output_tokens),
                ),
            }
            arm_payloads = {
                "auto": {**common, "model": "auto"},
                "deep": {**common, "model": config.tiers[RouteTier.DEEP].model},
            }
            for arm in ("auto", "deep"):
                key = (case["id"], arm)
                if key in completions:
                    continue
                completed_spend, unresolved_spend, cap_spend = accounted_spend(
                    completions, reservations
                )
                ceiling = request_cost_ceiling(
                    arm_payloads[arm],
                    config,
                    attempt_multiplier=2 if arm == "auto" else 1,
                )
                reservation = reserve_call(
                    args.output,
                    fingerprint=fingerprint,
                    case_id=case["id"],
                    arm=arm,
                    ceiling_usd=ceiling,
                    cap_accounted_spend=cap_spend,
                    max_cost_usd=args.max_cost_usd,
                )
                if reservation is None:
                    print(
                        f"budget stop before {case['id']}:{arm}: ${cap_spend:.6f} "
                        f"accounted, ${ceiling:.6f} next-call ceiling",
                        flush=True,
                    )
                    failed = False
                    break
                reservations[str(reservation["reservation_id"])] = reservation
                try:
                    result = request(client, arm_payloads[arm], config)
                except BenchmarkRequestError as exc:
                    failure = failure_record(case["id"], arm, exc)
                    failure_path.write_text(
                        json.dumps(failure, indent=2) + "\n", encoding="utf-8"
                    )
                    print(str(exc), flush=True)
                    failed = True
                    break
                completion = complete_call(args.output, reservation, result)
                reservations.pop(str(reservation["reservation_id"]), None)
                completions[key] = completion
            else:
                auto = completions[(case["id"], "auto")]["result"]
                deep = completions[(case["id"], "deep")]["result"]
                if not args.no_judge and (case["id"], "judge") not in completions:
                    payload, auto_is_a = judge_payload(
                        case, auto, deep, config, args.judge_output_tokens
                    )
                    _, _, cap_spend = accounted_spend(completions, reservations)
                    ceiling = request_cost_ceiling(payload, config)
                    reservation = reserve_call(
                        args.output,
                        fingerprint=fingerprint,
                        case_id=case["id"],
                        arm="judge",
                        ceiling_usd=ceiling,
                        cap_accounted_spend=cap_spend,
                        max_cost_usd=args.max_cost_usd,
                    )
                    if reservation is None:
                        print(
                            f"budget stop before {case['id']}:judge: ${cap_spend:.6f} "
                            f"accounted, ${ceiling:.6f} next-call ceiling",
                            flush=True,
                        )
                        break
                    reservations[str(reservation["reservation_id"])] = reservation
                    try:
                        raw_judge = request(client, payload, config)
                        result = judge_result(raw_judge, auto_is_a=auto_is_a)
                        result["estimated_cost_from_measured_usage_usd"] = raw_judge[
                            "estimated_cost_from_measured_usage_usd"
                        ]
                        result["cost_comparison_eligible"] = raw_judge[
                            "cost_comparison_eligible"
                        ]
                    except BenchmarkRequestError as exc:
                        failure = failure_record(case["id"], "judge", exc)
                        failure_path.write_text(
                            json.dumps(failure, indent=2) + "\n", encoding="utf-8"
                        )
                        print(str(exc), flush=True)
                        failed = True
                        break
                    completion = complete_call(args.output, reservation, result)
                    reservations.pop(str(reservation["reservation_id"]), None)
                    completions[(case["id"], "judge")] = completion
                _, _, cap_spend = accounted_spend(completions, reservations)
                print(f"{case['id']}: ${cap_spend:.6f} cap-accounted", flush=True)
                continue
            break

    paired_ids = sorted(
        case_id
        for case_id in {key[0] for key in completions}
        if (case_id, "auto") in completions and (case_id, "deep") in completions
    )
    eligible_ids = [
        case_id
        for case_id in paired_ids
        if completions[(case_id, "auto")]["result"].get("cost_comparison_eligible")
        and completions[(case_id, "deep")]["result"].get("cost_comparison_eligible")
    ]
    auto_cost = sum(
        completions[(case_id, "auto")]["result"][
            "estimated_cost_from_measured_usage_usd"
        ]
        for case_id in eligible_ids
    )
    deep_cost = sum(
        completions[(case_id, "deep")]["result"][
            "estimated_cost_from_measured_usage_usd"
        ]
        for case_id in eligible_ids
    )
    judged = [
        completions[(case_id, "judge")]["result"]
        for case_id in eligible_ids
        if (case_id, "judge") in completions
    ]
    completed_spend, unresolved_spend, cap_spend = accounted_spend(
        completions, reservations
    )
    summary = {
        "paired_cases": len(paired_ids),
        "cost_comparison_eligible_cases": len(eligible_ids),
        "excluded_case_ids": sorted(set(paired_ids) - set(eligible_ids)),
        "experiment_fingerprint": fingerprint,
        "price_version": config.price_version,
        "requested_service_tier": SERVICE_TIER,
        "auto_estimated_cost_from_measured_usage_usd": round(auto_cost, 6),
        "always_deep_estimated_cost_from_measured_usage_usd": round(deep_cost, 6),
        "completed_budget_accounted_spend_usd": round(completed_spend, 6),
        "unresolved_reserved_spend_usd": round(unresolved_spend, 6),
        "cap_accounted_spend_usd": round(cap_spend, 6),
        "estimated_savings_from_measured_usage_percent": (
            round((deep_cost - auto_cost) / deep_cost * 100, 2) if deep_cost else None
        ),
        "auto_quality_mean": (
            round(statistics.mean(row["auto_score"] for row in judged), 3)
            if judged
            else None
        ),
        "deep_quality_mean": (
            round(statistics.mean(row["deep_score"] for row in judged), 3)
            if judged
            else None
        ),
        "quality_delta": (
            round(
                statistics.mean(
                    row["auto_score"] - row["deep_score"] for row in judged
                ),
                3,
            )
            if judged
            else None
        ),
        "fallback_rate": (
            round(
                sum(
                    bool(completions[(case_id, "auto")]["result"]["fallback_used"])
                    for case_id in paired_ids
                )
                / len(paired_ids),
                4,
            )
            if paired_ids
            else None
        ),
        "release_gate_note": (
            "This runner currently supports only stateless, no-tool cases. Fallback, failed-validation, "
            "or unverified-service-tier cases are excluded from cost comparison. API routing remains Beta."
        ),
    }
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if not failed and not reservations and failure_path.exists():
        failure_path.unlink()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
