from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def benchmark_module():
    path = ROOT / "evals" / "router-v2" / "benchmark.py"
    spec = importlib.util.spec_from_file_location("layman_test_api_benchmark", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def health_for(config):
    benchmark = benchmark_module()
    return {
        "price_version": config.price_version,
        "tiers": {tier.value: spec.model for tier, spec in config.tiers.items()},
        "routing_config_sha256": benchmark.routing_config_sha256(config),
        "upstream_identity_sha256": benchmark.upstream_identity_sha256(config),
    }


def test_live_benchmark_rejects_state_and_tools_before_execution():
    benchmark = benchmark_module()
    selected = [
        {"id": "state", "request": {"previous_response_id": "resp_fake"}},
        {"id": "tools", "request": {"tools": [{"type": "function"}]}},
    ]
    assert benchmark.unsupported_live_cases(selected) == {
        "previous_response_id": ["state"],
        "tools": ["tools"],
    }


def test_fingerprint_binds_cases_router_and_base_url(router_config):
    benchmark = benchmark_module()
    selected = [{"id": "one", "input": "hello", "request": {"input": "hello"}}]
    health = health_for(router_config)
    current, payload = benchmark.benchmark_fingerprint(
        selected,
        router_config,
        max_output_tokens=100,
        judge_output_tokens=50,
        with_judge=True,
        base_url="http://127.0.0.1:8787",
        health=health,
    )
    same, _ = benchmark.benchmark_fingerprint(
        selected,
        router_config,
        max_output_tokens=100,
        judge_output_tokens=50,
        with_judge=True,
        base_url="http://127.0.0.1:8787/",
        health=health,
    )
    changed, _ = benchmark.benchmark_fingerprint(
        selected,
        router_config,
        max_output_tokens=100,
        judge_output_tokens=50,
        with_judge=True,
        base_url="http://localhost:8787",
        health=health,
    )
    assert current == same
    assert current != changed
    assert payload["judge_instructions"] == benchmark.JUDGE_INSTRUCTIONS
    assert payload["router_config"]["projects"]


def test_wal_keeps_inflight_reservation_and_does_not_repeat_completion(
    tmp_path: Path,
):
    benchmark = benchmark_module()
    output = tmp_path / "benchmark.jsonl"
    reservation = benchmark.reserve_call(
        output,
        fingerprint="fingerprint",
        case_id="case",
        arm="auto",
        ceiling_usd=0.25,
        cap_accounted_spend=0,
        max_cost_usd=1,
    )
    assert reservation is not None
    completions, reservations = benchmark.load_events(output, "fingerprint")
    assert not completions
    assert list(reservations) == [reservation["reservation_id"]]
    assert benchmark.accounted_spend(completions, reservations) == (0, 0.25, 0.25)

    completion = benchmark.complete_call(
        output,
        reservation,
        {
            "estimated_cost_from_measured_usage_usd": 0.1,
            "cost_comparison_eligible": True,
        },
    )
    completions, reservations = benchmark.load_events(output, "fingerprint")
    assert not reservations
    assert completions[("case", "auto")] == completion
    assert benchmark.accounted_spend(completions, reservations) == (0.1, 0, 0.1)


def test_ineligible_fallback_accounts_full_reserved_ceiling(tmp_path: Path):
    benchmark = benchmark_module()
    output = tmp_path / "benchmark.jsonl"
    reservation = benchmark.reserve_call(
        output,
        fingerprint="fingerprint",
        case_id="case",
        arm="auto",
        ceiling_usd=0.25,
        cap_accounted_spend=0,
        max_cost_usd=1,
    )
    assert reservation is not None
    completion = benchmark.complete_call(
        output,
        reservation,
        {
            "estimated_cost_from_measured_usage_usd": 0.05,
            "cost_comparison_eligible": False,
            "fallback_used": True,
        },
    )
    assert completion["accounted_cost_usd"] == 0.25


def test_judge_request_uses_locked_service_tier(router_config):
    benchmark = benchmark_module()
    case = {"id": "case", "input": "question"}
    answer = {"text": "answer"}
    payload, _ = benchmark.judge_payload(case, answer, answer, router_config, 64)
    assert payload["service_tier"] == "default"
    assert payload["max_output_tokens"] == 64


def test_router_health_mismatch_is_rejected(router_config):
    benchmark = benchmark_module()
    router_config.upstream_base_url = "https://api.openai.com/v1"
    health = health_for(router_config)
    benchmark.validate_router_health(health, router_config)
    changed = json.loads(json.dumps(health))
    changed["tiers"]["fast"] = "other-model"
    try:
        benchmark.validate_router_health(changed, router_config)
    except RuntimeError as exc:
        assert "tiers differ" in str(exc)
    else:
        raise AssertionError("mismatched router health was accepted")


def test_real_api_benchmark_rejects_non_openai_upstream(router_config):
    benchmark = benchmark_module()
    router_config.upstream_base_url = "http://127.0.0.1:9999/v1"
    health = health_for(router_config)
    try:
        benchmark.validate_router_health(health, router_config)
    except RuntimeError as exc:
        assert "official OpenAI upstream" in str(exc)
    else:
        raise AssertionError("non-OpenAI benchmark upstream was accepted")
