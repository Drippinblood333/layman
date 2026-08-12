from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .models import ModelPricing, RouterConfig, RouteTier, UsageRecord
from .paths import layman_home, mark_layman_home_owned


SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_log (
  request_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  prompt_hash TEXT NOT NULL,
  task_type TEXT NOT NULL,
  complexity TEXT NOT NULL,
  risk TEXT NOT NULL,
  route_tier TEXT NOT NULL,
  selected_model TEXT NOT NULL,
  reasoning_effort TEXT NOT NULL,
  route_reason_json TEXT NOT NULL,
  input_tokens INTEGER NOT NULL,
  cached_tokens INTEGER NOT NULL,
  cache_write_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  reasoning_tokens INTEGER NOT NULL,
  latency_ms INTEGER NOT NULL,
  estimated_cost_usd REAL NOT NULL,
  estimated_always_deep_cost_usd REAL NOT NULL,
  fallback_used INTEGER NOT NULL,
  validator_passed INTEGER,
  error_category TEXT,
  upstream_request_id TEXT,
  metadata_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_log(created_at);
CREATE INDEX IF NOT EXISTS idx_usage_project ON usage_log(project_id, created_at);
"""


def estimate_cost(usage: dict[str, int], pricing: ModelPricing) -> float:
    input_tokens = max(0, int(usage.get("input_tokens", 0)))
    cached_tokens = min(input_tokens, max(0, int(usage.get("cached_tokens", 0))))
    cache_write_tokens = max(0, int(usage.get("cache_write_tokens", 0)))
    output_tokens = max(0, int(usage.get("output_tokens", 0)))
    cache_write_tokens = min(input_tokens - cached_tokens, cache_write_tokens)
    uncached = input_tokens - cached_tokens - cache_write_tokens
    rates = pricing.long_context if pricing.long_context and input_tokens > pricing.long_context.threshold_tokens else pricing
    total = (
        uncached * rates.input_per_million
        + cached_tokens * rates.cached_input_per_million
        + output_tokens * rates.output_per_million
    ) / 1_000_000
    if rates.cache_write_per_million is not None:
        total += cache_write_tokens * rates.cache_write_per_million / 1_000_000
    return round(total, 9)


def extract_usage(response: dict[str, Any] | None) -> dict[str, int]:
    raw = (response or {}).get("usage") or {}
    input_details = raw.get("input_tokens_details") or {}
    output_details = raw.get("output_tokens_details") or {}
    return {
        "input_tokens": int(raw.get("input_tokens") or 0),
        "cached_tokens": int(input_details.get("cached_tokens") or 0),
        "cache_write_tokens": int(input_details.get("cache_write_tokens") or 0),
        "output_tokens": int(raw.get("output_tokens") or 0),
        "reasoning_tokens": int(output_details.get("reasoning_tokens") or 0),
    }


class UsageStore:
    def __init__(self, database_path: str, config: RouterConfig):
        self.path = Path(database_path)
        self.config = config

    def initialize(self) -> None:
        created_parent = not self.path.parent.exists()
        if self.path.parent.expanduser().resolve() == layman_home():
            mark_layman_home_owned(self.path.parent)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        if created_parent:
            try:
                self.path.parent.chmod(0o700)
            except OSError:
                pass
        with sqlite3.connect(self.path) as connection:
            connection.executescript(SCHEMA)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def prune(self) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.config.telemetry_retention_days)).isoformat()
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute("DELETE FROM usage_log WHERE created_at < ?", (cutoff,))
            return cursor.rowcount

    def healthy(self) -> bool:
        try:
            with sqlite3.connect(self.path) as connection:
                connection.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False

    def add(self, record: UsageRecord) -> None:
        values = record.model_dump()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                INSERT INTO usage_log VALUES (
                  :request_id, :project_id, :prompt_hash, :task_type, :complexity, :risk,
                  :route_tier, :selected_model, :reasoning_effort, :route_reason_json,
                  :input_tokens, :cached_tokens, :cache_write_tokens, :output_tokens,
                  :reasoning_tokens, :latency_ms, :estimated_cost_usd,
                  :estimated_always_deep_cost_usd, :fallback_used, :validator_passed,
                  :error_category, :upstream_request_id, :metadata_json, :created_at
                )
                """,
                {
                    **values,
                    "route_reason_json": json.dumps(values.pop("route_reason"), ensure_ascii=False),
                    "metadata_json": json.dumps(values.pop("metadata"), ensure_ascii=False),
                    "fallback_used": int(record.fallback_used),
                    "validator_passed": None if record.validator_passed is None else int(record.validator_passed),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )

    def summary(self, *, project_id: str | None = None, start: str | None = None, end: str | None = None) -> dict[str, Any]:
        params = {"project_id": project_id, "start": start, "end": end}
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT COUNT(*) total_requests,
                       COALESCE(SUM(estimated_cost_usd), 0) total_cost_usd,
                       COALESCE(SUM(CASE
                           WHEN COALESCE(json_extract(metadata_json, '$.automatic'), 1) = 1
                            AND COALESCE(json_extract(metadata_json, '$.cost_estimate_available'), 1) = 1
                            AND COALESCE(json_extract(metadata_json, '$.usage_incomplete'), 0) = 0
                           THEN estimated_cost_usd ELSE 0 END), 0) estimated_automatic_cost_usd,
                       COALESCE(SUM(CASE
                           WHEN COALESCE(json_extract(metadata_json, '$.automatic'), 1) = 1
                            AND COALESCE(json_extract(metadata_json, '$.cost_estimate_available'), 1) = 1
                            AND COALESCE(json_extract(metadata_json, '$.usage_incomplete'), 0) = 0
                           THEN estimated_always_deep_cost_usd ELSE 0 END), 0) estimated_always_deep_cost_usd,
                       COALESCE(SUM(CASE
                           WHEN COALESCE(json_extract(metadata_json, '$.automatic'), 1) = 1
                           THEN 1 ELSE 0 END), 0) automatic_requests,
                       COALESCE(SUM(CASE
                           WHEN COALESCE(json_extract(metadata_json, '$.automatic'), 1) = 1
                            AND COALESCE(json_extract(metadata_json, '$.cost_estimate_available'), 1) = 1
                            AND COALESCE(json_extract(metadata_json, '$.usage_incomplete'), 0) = 0
                           THEN 1 ELSE 0 END), 0) savings_eligible_requests,
                       COALESCE(SUM(CASE
                           WHEN COALESCE(json_extract(metadata_json, '$.cost_estimate_available'), 1) = 0
                           THEN 1 ELSE 0 END), 0) unpriced_requests,
                       COALESCE(SUM(CASE
                           WHEN COALESCE(json_extract(metadata_json, '$.usage_incomplete'), 0) = 1
                           THEN 1 ELSE 0 END), 0) usage_incomplete_requests,
                       COALESCE(AVG(latency_ms), 0) average_latency_ms,
                       COALESCE(AVG(fallback_used), 0) fallback_rate,
                       AVG(CASE WHEN validator_passed IS NOT NULL THEN validator_passed END) validator_pass_rate,
                       COALESCE(SUM(input_tokens), 0) input_tokens,
                       COALESCE(SUM(cached_tokens), 0) cached_tokens,
                       COALESCE(SUM(cache_write_tokens), 0) cache_write_tokens,
                       COALESCE(SUM(output_tokens), 0) output_tokens,
                       COALESCE(SUM(reasoning_tokens), 0) reasoning_tokens
                FROM usage_log
                WHERE (:project_id IS NULL OR project_id = :project_id)
                  AND (:start IS NULL OR created_at >= :start)
                  AND (:end IS NULL OR created_at <= :end)
                """,
                params,
            ).fetchone()
            route_rows = connection.execute(
                """SELECT route_tier, COUNT(*) count FROM usage_log
                   WHERE (:project_id IS NULL OR project_id = :project_id)
                     AND (:start IS NULL OR created_at >= :start)
                     AND (:end IS NULL OR created_at <= :end)
                   GROUP BY route_tier ORDER BY route_tier""",
                params,
            ).fetchall()
        result = dict(row)
        result["routes"] = {item["route_tier"]: item["count"] for item in route_rows}
        baseline = float(result["estimated_always_deep_cost_usd"])
        actual = float(result["estimated_automatic_cost_usd"])
        savings = baseline - actual
        result["estimated_savings_usd"] = round(savings, 6)
        result["estimated_savings_percent"] = round((savings / baseline * 100) if baseline else 0, 2)
        result["total_cost_is_partial"] = bool(result["unpriced_requests"] or result["usage_incomplete_requests"])
        result["measured_savings_usd"] = None
        result["measurement_note"] = (
            "Estimated signed savings compare only complete, priced automatic requests with the same observed "
            "token counts at deep-tier prices; unpriced or incomplete requests are reported separately."
        )
        result["price_version"] = self.config.price_version
        return result

    def recent(self, *, limit: int = 50, project_id: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        params: tuple[Any, ...] = (project_id, project_id, limit)
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT request_id, project_id, task_type, complexity, risk, route_tier,
                       selected_model, reasoning_effort, route_reason_json, input_tokens,
                       cached_tokens, cache_write_tokens, output_tokens, reasoning_tokens, latency_ms,
                       estimated_cost_usd, estimated_always_deep_cost_usd, fallback_used,
                       validator_passed, error_category, metadata_json, created_at
                FROM usage_log
                WHERE (? IS NULL OR project_id = ?)
                ORDER BY created_at DESC LIMIT ?
                """,
                params,
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["route_reason"] = json.loads(item.pop("route_reason_json"))
            metadata = json.loads(item.pop("metadata_json"))
            item["fallback_used"] = bool(item["fallback_used"])
            item["validator_passed"] = None if item["validator_passed"] is None else bool(item["validator_passed"])
            item["automatic"] = bool(metadata.get("automatic", True))
            item["cost_estimate_available"] = bool(metadata.get("cost_estimate_available", True))
            item["usage_incomplete"] = bool(metadata.get("usage_incomplete", False))
            item["cost_estimate_complete"] = bool(metadata.get(
                "cost_estimate_complete", item["cost_estimate_available"] and not item["usage_incomplete"]
            ))
            item["attempt_count"] = int(metadata.get("attempt_count", 1))
            item["unpriced_attempts"] = int(metadata.get("unpriced_attempts", 0))
            item["attempts"] = metadata.get("attempts", [])
            result.append(item)
        return result

    def routing_analysis(self) -> dict[str, Any]:
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT task_type, risk, route_tier, COUNT(*) requests,
                       AVG(latency_ms) average_latency_ms,
                       AVG(fallback_used) fallback_rate,
                       AVG(CASE WHEN validator_passed IS NOT NULL THEN validator_passed END) validator_pass_rate,
                       SUM(estimated_cost_usd) cost_usd
                FROM usage_log
                GROUP BY task_type, risk, route_tier
                ORDER BY requests DESC
                """
            ).fetchall()
        return {"segments": [dict(row) for row in rows], "price_version": self.config.price_version}


def price_for_model(config: RouterConfig, model: str) -> ModelPricing | None:
    for tier in RouteTier:
        if config.tiers[tier].model == model:
            return config.tiers[tier].pricing
    return None
