from __future__ import annotations

from layman_router.models import UsageRecord
from layman_router.telemetry import UsageStore, estimate_cost, extract_usage
from layman_router.validation import validate_response
from layman_router.demo import seed_demo


def completed(text: str = "ok"):
    return {
        "status": "completed",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
        "usage": {
            "input_tokens": 1000,
            "input_tokens_details": {"cached_tokens": 400},
            "output_tokens": 100,
            "output_tokens_details": {"reasoning_tokens": 20},
        },
    }


def test_structured_output_validation():
    request = {"text": {"format": {"type": "json_schema", "schema": {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}}}}
    assert validate_response(completed('{"ok":true}'), request).passed
    assert not validate_response(completed('{"wrong":true}'), request).passed


def test_incomplete_and_empty_fail_validation():
    assert not validate_response({"status": "incomplete", "output": []}, {}).passed
    assert not validate_response({"status": "completed", "output": []}, {}).passed


def test_cost_counts_cached_tokens_once(router_config):
    usage = extract_usage(completed())
    price = router_config.tiers["fast"].pricing
    expected = ((600 * 0.2) + (400 * 0.02) + (100 * 1.2)) / 1_000_000
    assert estimate_cost(usage, price) == expected


def test_cost_replaces_uncached_rate_with_cache_write_rate(router_config):
    usage = {"input_tokens": 1000, "cached_tokens": 200, "cache_write_tokens": 300, "output_tokens": 0}
    price = router_config.tiers["fast"].pricing
    expected = ((500 * 0.2) + (200 * 0.02) + (300 * 0.25)) / 1_000_000
    assert estimate_cost(usage, price) == expected


def test_cost_uses_long_context_rates_above_272k(router_config):
    price = router_config.tiers["fast"].pricing
    short = {"input_tokens": 272_000, "cached_tokens": 0, "cache_write_tokens": 0, "output_tokens": 1000}
    long = {"input_tokens": 272_001, "cached_tokens": 0, "cache_write_tokens": 0, "output_tokens": 1000}
    assert estimate_cost(short, price) == round(((272_000 * 0.2) + (1000 * 1.2)) / 1_000_000, 9)
    assert estimate_cost(long, price) == round(((272_001 * 0.4) + (1000 * 1.8)) / 1_000_000, 9)


def test_official_2026_07_30_standard_prices_are_loaded(router_config):
    assert router_config.price_version == "openai-standard-2026-07-30"
    expected = {
        "fast": (0.2, 0.02, 0.25, 1.2, 0.4, 0.04, 0.5, 1.8),
        "balanced": (2.0, 0.2, 2.5, 12.0, 4.0, 0.4, 5.0, 18.0),
        "deep": (5.0, 0.5, 6.25, 30.0, 10.0, 1.0, 12.5, 45.0),
    }
    for tier, values in expected.items():
        price = router_config.tiers[tier].pricing
        assert price.long_context is not None
        assert price.long_context.threshold_tokens == 272_000
        assert (
            price.input_per_million,
            price.cached_input_per_million,
            price.cache_write_per_million,
            price.output_per_million,
            price.long_context.input_per_million,
            price.long_context.cached_input_per_million,
            price.long_context.cache_write_per_million,
            price.long_context.output_per_million,
        ) == values


def test_store_summary_has_estimate_label(router_config):
    store = UsageStore(router_config.database_path, router_config)
    store.initialize()
    store.add(UsageRecord(
        request_id="one", project_id="default", prompt_hash="a" * 64,
        task_type="summary", complexity="low", risk="low", route_tier="fast",
        selected_model="gpt-5.6-luna", reasoning_effort="low", route_reason=["test"],
        input_tokens=1000, output_tokens=100, latency_ms=10,
        estimated_cost_usd=0.0016, estimated_always_deep_cost_usd=0.008,
    ))
    result = store.summary()
    assert result["total_requests"] == 1
    assert result["estimated_savings_usd"] > 0
    assert result["measured_savings_usd"] is None
    assert result["routes"] == {"fast": 1}
    assert result["cache_write_tokens"] == 0
    assert "Estimated" in result["measurement_note"]


def test_demo_seed_is_synthetic_and_populates_all_tiers(router_config):
    store = UsageStore(router_config.database_path, router_config)
    store.initialize()
    seed_demo(store, router_config, count=20)
    summary = store.summary(project_id="demo-project")
    assert summary["total_requests"] == 20
    assert summary["routes"] == {"balanced": 6, "deep": 4, "fast": 10}
    assert all(item["request_id"].startswith("demo-") for item in store.recent(limit=20))
