from __future__ import annotations

import asyncio
import json
import os
import secrets
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse

from .cache_policy import PromptCachePolicy, prepare_upstream_payload
from .classify import classify_task
from .config import load_config, routing_config_sha256, upstream_identity_sha256
from .context_opt import ContextOptimization, optimize_payload
from .models import RouteDecision, RouterConfig, RouteTier, TaskFeatures, UsageRecord
from .provider import StreamHandle, UpstreamProvider
from .routing import apply_route, decide_route, explicit_model_decision, fallback_decision
from .streaming import SSECapture
from .telemetry import UsageStore, estimate_cost, extract_usage, price_for_model
from .validation import validate_response


RETRYABLE_STATUS = {429, 500, 502, 503, 504}
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
ASSET_ROOT = Path(__file__).with_name("dashboard")
USAGE_KEYS = ("input_tokens", "cached_tokens", "cache_write_tokens", "output_tokens", "reasoning_tokens")


def _require_admin(request: Request, settings: RouterConfig) -> None:
    host = request.client.host if request.client else ""
    if host not in LOOPBACK_HOSTS and not settings.admin_allow_non_loopback:
        raise HTTPException(status_code=403, detail="Admin endpoint is loopback-only")
    expected = os.getenv(settings.admin_token_env)
    supplied = request.headers.get("x-layman-admin-token")
    if not expected:
        raise HTTPException(status_code=503, detail=f"Set {settings.admin_token_env} before using admin endpoints")
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid admin token")


def _layman_headers(
    request_id: str,
    decision: RouteDecision,
    fallback_used: bool,
    optimization: ContextOptimization,
    cache_policy: PromptCachePolicy,
    validator_passed: bool | None = None,
) -> dict[str, str]:
    result = {
        "x-layman-request-id": request_id,
        "x-layman-route-tier": decision.route_tier.value,
        "x-layman-selected-model": decision.selected_model,
        "x-layman-fallback-used": str(fallback_used).lower(),
        "x-layman-context-mode": optimization.mode,
        "x-layman-context-duplicates-removed": str(optimization.duplicate_blocks_removed),
        "x-layman-prompt-cache-mode": cache_policy.mode,
        "x-layman-prompt-cache-breakpoints": str(cache_policy.breakpoints),
    }
    if validator_passed is not None:
        result["x-layman-validator-passed"] = str(validator_passed).lower()
    return result


def _usage_record(
    *,
    request_id: str,
    features: TaskFeatures,
    decision: RouteDecision,
    config: RouterConfig,
    attempts: list[dict[str, Any]],
    latency_ms: int,
    fallback_used: bool,
    validator_passed: bool | None,
    error_category: str | None,
    upstream_request_id: str | None,
    optimization: ContextOptimization,
    cache_policy: PromptCachePolicy,
) -> UsageRecord:
    usage = {key: sum(int(attempt["usage"].get(key, 0)) for attempt in attempts) for key in USAGE_KEYS}
    actual = 0.0
    unpriced_attempts = 0
    public_attempts: list[dict[str, Any]] = []
    for attempt in attempts:
        pricing = price_for_model(config, str(attempt["selected_model"]))
        attempt_cost = estimate_cost(attempt["usage"], pricing) if pricing else 0.0
        if pricing is None:
            unpriced_attempts += 1
        public_attempts.append({
            **attempt,
            "cost_estimate_available": pricing is not None,
            "estimated_cost_usd": attempt_cost,
        })
        actual += attempt_cost
    usage_incomplete = not attempts or any(not bool(attempt["usage_available"]) for attempt in attempts)
    cost_estimate_available = unpriced_attempts == 0
    cost_estimate_complete = cost_estimate_available and not usage_incomplete
    savings_eligible = decision.automatic and cost_estimate_complete
    baseline = (
        round(sum(estimate_cost(attempt["usage"], config.tiers[RouteTier.DEEP].pricing) for attempt in attempts), 9)
        if savings_eligible
        else 0.0
    )
    return UsageRecord(
        request_id=request_id,
        project_id=features.project_id,
        prompt_hash=features.prompt_hash,
        task_type=features.task_type.value,
        complexity=features.complexity,
        risk=features.risk,
        route_tier=decision.route_tier.value,
        selected_model=decision.selected_model,
        reasoning_effort=decision.reasoning_effort,
        route_reason=decision.route_reason,
        **usage,
        latency_ms=latency_ms,
        estimated_cost_usd=round(actual, 9),
        estimated_always_deep_cost_usd=baseline,
        fallback_used=fallback_used,
        validator_passed=validator_passed,
        error_category=error_category,
        upstream_request_id=upstream_request_id,
        metadata={
            "price_version": config.price_version,
            "automatic": decision.automatic,
            "cost_estimate_available": cost_estimate_available,
            "cost_estimate_complete": cost_estimate_complete,
            "savings_eligible": savings_eligible,
            "usage_incomplete": usage_incomplete,
            "attempt_count": len(attempts),
            "unpriced_attempts": unpriced_attempts,
            "attempts": public_attempts,
            "context_mode": optimization.mode,
            "context_original_chars": optimization.original_chars,
            "context_optimized_chars": optimization.optimized_chars,
            "context_duplicate_blocks_removed": optimization.duplicate_blocks_removed,
            "prompt_cache_mode": cache_policy.mode,
            "prompt_cache_breakpoints": cache_policy.breakpoints,
        },
    )


def _usage_attempt(
    decision: RouteDecision,
    response: dict[str, Any] | None,
    outcome: str,
) -> dict[str, Any]:
    raw_usage = response.get("usage") if isinstance(response, dict) else None
    usage_available = (
        isinstance(raw_usage, dict)
        and isinstance(raw_usage.get("input_tokens"), int)
        and isinstance(raw_usage.get("output_tokens"), int)
    )
    return {
        "selected_model": decision.selected_model,
        "route_tier": decision.route_tier.value,
        "outcome": outcome,
        "usage_available": usage_available,
        "usage": extract_usage(response if usage_available else None),
    }


def _json_object(value: bytes) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def create_app(
    config: RouterConfig | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = config or load_config()
    store = UsageStore(settings.database_path, settings)
    store.initialize()
    store.prune()
    provider = UpstreamProvider(settings.upstream_base_url, transport=transport, timeout_seconds=settings.upstream_timeout_seconds)
    app = FastAPI(title="Layman", version="1.0.0", docs_url=None, redoc_url=None)
    app.state.config = settings
    app.state.store = store
    app.state.provider = provider

    @app.get("/healthz")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok" if store.healthy() else "degraded",
            "database": "ok" if store.healthy() else "error",
            "price_version": settings.price_version,
            "tiers": {tier.value: spec.model for tier, spec in settings.tiers.items()},
            "routing_config_sha256": routing_config_sha256(settings),
            "upstream_identity_sha256": upstream_identity_sha256(settings),
            "dashboard": "/admin/" if settings.dashboard_enabled else None,
            "demo_mode": settings.demo_mode,
        }

    @app.get("/admin", include_in_schema=False)
    async def admin_redirect() -> Response:
        if not settings.dashboard_enabled:
            raise HTTPException(status_code=404)
        return RedirectResponse("/admin/")

    @app.get("/admin/", include_in_schema=False)
    async def admin_dashboard() -> Response:
        if not settings.dashboard_enabled:
            raise HTTPException(status_code=404)
        return HTMLResponse(
            (ASSET_ROOT / "index.html").read_text(encoding="utf-8"),
            headers={
                "cache-control": "no-store",
                "content-security-policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'",
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
                "referrer-policy": "no-referrer",
            },
        )

    @app.get("/admin/assets/{name}", include_in_schema=False)
    async def admin_asset(name: str) -> Response:
        if not settings.dashboard_enabled or name not in {"dashboard.css", "dashboard.js"}:
            raise HTTPException(status_code=404)
        return FileResponse(ASSET_ROOT / name, headers={"cache-control": "no-store", "x-content-type-options": "nosniff"})

    @app.get("/v1/models")
    async def models() -> dict[str, Any]:
        created = int(time.time())
        ids = ["auto", *dict.fromkeys(spec.model for spec in settings.tiers.values())]
        return {"object": "list", "data": [{"id": item, "object": "model", "created": created, "owned_by": "layman"} for item in ids]}

    @app.get("/admin/usage/summary")
    async def usage_summary(
        request: Request,
        project_id: str | None = None,
        start: str | None = Query(default=None, alias="from"),
        end: str | None = Query(default=None, alias="to"),
    ) -> dict[str, Any]:
        _require_admin(request, settings)
        return await asyncio.to_thread(store.summary, project_id=project_id, start=start, end=end)

    @app.get("/admin/usage/recent")
    async def usage_recent(request: Request, limit: int = 50, project_id: str | None = None) -> dict[str, Any]:
        _require_admin(request, settings)
        return {"requests": await asyncio.to_thread(store.recent, limit=limit, project_id=project_id)}

    @app.get("/admin/routing/analysis")
    async def routing_analysis(request: Request) -> dict[str, Any]:
        _require_admin(request, settings)
        return await asyncio.to_thread(store.routing_analysis)

    @app.post("/v1/responses")
    async def responses(request: Request) -> Response:
        if settings.demo_mode:
            raise HTTPException(status_code=403, detail="Responses forwarding is disabled in synthetic demo mode")
        try:
            payload = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Request body must be valid JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("model"), str):
            raise HTTPException(status_code=400, detail="Request must contain a string model")
        if "reasoning" in payload and not isinstance(payload["reasoning"], dict):
            raise HTTPException(status_code=400, detail="reasoning must be an object")
        if "max_output_tokens" in payload and (
            isinstance(payload["max_output_tokens"], bool)
            or not isinstance(payload["max_output_tokens"], int)
            or payload["max_output_tokens"] < 1
        ):
            raise HTTPException(status_code=400, detail="max_output_tokens must be a positive integer")
        if not request.headers.get("authorization"):
            raise HTTPException(status_code=401, detail="Authorization header is required")

        optimized_payload, optimization = optimize_payload(payload)
        features = classify_task(optimized_payload, settings)
        metadata = optimized_payload.get("metadata") if isinstance(optimized_payload.get("metadata"), dict) else {}
        decision = (
            decide_route(features, settings, metadata)
            if optimized_payload["model"] == "auto"
            else explicit_model_decision(optimized_payload, settings)
        )
        try:
            upstream_payload, cache_policy = prepare_upstream_payload(
                optimized_payload,
                automatic=decision.automatic,
                selected_model=decision.selected_model,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        headers = provider.request_headers(request.headers)
        request_id = str(uuid.uuid4())
        started = time.perf_counter()

        if optimized_payload.get("stream") is True:
            return await _stream_response(
                provider=provider,
                store=store,
                config=settings,
                payload=upstream_payload,
                headers=headers,
                features=features,
                decision=decision,
                request_id=request_id,
                started=started,
                optimization=optimization,
                cache_policy=cache_policy,
            )
        return await _nonstream_response(
            provider=provider,
            store=store,
            config=settings,
            payload=upstream_payload,
            headers=headers,
            features=features,
            decision=decision,
            request_id=request_id,
            started=started,
            optimization=optimization,
            cache_policy=cache_policy,
        )

    return app


async def _nonstream_response(
    *, provider: UpstreamProvider, store: UsageStore, config: RouterConfig, payload: dict[str, Any],
    headers: dict[str, str], features: TaskFeatures, decision: RouteDecision, request_id: str, started: float,
    optimization: ContextOptimization, cache_policy: PromptCachePolicy,
) -> Response:
    current = decision
    fallback_used = False
    error_category: str | None = None
    upstream: httpx.Response | None = None
    data: dict[str, Any] | None = None
    validation_passed: bool | None = None
    attempts: list[dict[str, Any]] = []

    for attempt in range(2):
        routed = apply_route(payload, current)
        try:
            upstream = await provider.post(routed, headers)
        except httpx.HTTPError:
            error_category = "upstream_network_error"
            attempts.append(_usage_attempt(current, None, error_category))
            fallback = fallback_decision(current, config) if attempt == 0 else None
            if fallback:
                current, fallback_used = fallback, True
                continue
            break
        try:
            parsed = upstream.json()
            data = parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            data = None
        if upstream.status_code in RETRYABLE_STATUS:
            error_category = f"upstream_http_{upstream.status_code}"
            attempts.append(_usage_attempt(current, data, error_category))
            fallback = fallback_decision(current, config) if attempt == 0 else None
            if fallback:
                current, fallback_used = fallback, True
                continue
            break
        if upstream.is_success and data is not None:
            validation = validate_response(data, routed)
            validation_passed = validation.passed
            if not validation.passed:
                error_category = validation.reason
                attempts.append(_usage_attempt(current, data, error_category or "validation_failed"))
                fallback = fallback_decision(current, config) if attempt == 0 else None
                if fallback:
                    current, fallback_used = fallback, True
                    continue
            else:
                error_category = None
                attempts.append(_usage_attempt(current, data, "completed"))
        else:
            error_category = f"upstream_http_{upstream.status_code}" if not upstream.is_success else "invalid_upstream_json"
            attempts.append(_usage_attempt(current, data, error_category))
        break

    latency_ms = int((time.perf_counter() - started) * 1000)
    upstream_id = upstream.headers.get("openai-request-id") if upstream else None
    record = _usage_record(
        request_id=request_id, features=features, decision=current, config=config, attempts=attempts,
        latency_ms=latency_ms, fallback_used=fallback_used, validator_passed=validation_passed,
        error_category=error_category, upstream_request_id=upstream_id,
        optimization=optimization,
        cache_policy=cache_policy,
    )
    await asyncio.to_thread(store.add, record)
    if upstream is None:
        return JSONResponse(status_code=502, headers=_layman_headers(request_id, current, fallback_used, optimization, cache_policy), content={"error": {"message": "Upstream request failed", "type": "layman_router_error"}})
    response_headers = provider.response_headers(upstream.headers)
    response_headers.update(
        _layman_headers(
            request_id,
            current,
            fallback_used,
            optimization,
            cache_policy,
            validator_passed=validation_passed,
        )
    )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type", "application/json").split(";", 1)[0],
    )


async def _stream_response(
    *, provider: UpstreamProvider, store: UsageStore, config: RouterConfig, payload: dict[str, Any],
    headers: dict[str, str], features: TaskFeatures, decision: RouteDecision, request_id: str, started: float,
    optimization: ContextOptimization, cache_policy: PromptCachePolicy,
) -> Response:
    current = decision
    fallback_used = False
    handle: StreamHandle | None = None
    error_category: str | None = None
    attempts: list[dict[str, Any]] = []

    for attempt in range(2):
        routed = apply_route(payload, current)
        try:
            handle = await provider.stream(routed, headers)
        except httpx.HTTPError:
            error_category = "upstream_network_error"
            attempts.append(_usage_attempt(current, None, error_category))
            fallback = fallback_decision(current, config) if attempt == 0 else None
            if fallback:
                current, fallback_used = fallback, True
                continue
            break
        if handle.response.status_code in RETRYABLE_STATUS or (handle.response.is_success and not handle.first_chunk):
            error_category = f"upstream_http_{handle.response.status_code}" if handle.response.status_code in RETRYABLE_STATUS else "empty_stream"
            fallback = fallback_decision(current, config) if attempt == 0 else None
            if fallback:
                attempts.append(_usage_attempt(current, _json_object(handle.first_chunk), error_category))
                await handle.close()
                handle = None
                current, fallback_used = fallback, True
                continue
        break

    if handle is None:
        record = _usage_record(
            request_id=request_id, features=features, decision=current, config=config, attempts=attempts,
            latency_ms=int((time.perf_counter() - started) * 1000), fallback_used=fallback_used,
            validator_passed=None, error_category=error_category, upstream_request_id=None,
            optimization=optimization,
            cache_policy=cache_policy,
        )
        await asyncio.to_thread(store.add, record)
        return JSONResponse(status_code=502, headers=_layman_headers(request_id, current, fallback_used, optimization, cache_policy), content={"error": {"message": "Upstream stream failed before first event", "type": "layman_router_error"}})

    if not handle.response.is_success:
        body = handle.first_chunk + await handle.response.aread()
        status = handle.response.status_code
        attempts.append(_usage_attempt(current, _json_object(body), error_category or f"upstream_http_{status}"))
        response_headers = provider.response_headers(handle.response.headers)
        response_headers.update(_layman_headers(request_id, current, fallback_used, optimization, cache_policy))
        await handle.close()
        record = _usage_record(
            request_id=request_id, features=features, decision=current, config=config, attempts=attempts,
            latency_ms=int((time.perf_counter() - started) * 1000), fallback_used=fallback_used,
            validator_passed=None, error_category=error_category or f"upstream_http_{status}",
            upstream_request_id=response_headers.get("openai-request-id"),
            optimization=optimization,
            cache_policy=cache_policy,
        )
        await asyncio.to_thread(store.add, record)
        return Response(content=body, status_code=status, headers=response_headers)

    capture = SSECapture()
    upstream_id = handle.response.headers.get("openai-request-id")
    if handle.first_chunk:
        error_category = None

    async def body() -> Any:
        stream_error: str | None = None
        try:
            capture.feed(handle.first_chunk)
            yield handle.first_chunk
            async for chunk in handle.iterator:
                capture.feed(chunk)
                yield chunk
        except httpx.HTTPError as exc:
            stream_error = "stream_interrupted_after_first_event"
            error = json.dumps({"type": "error", "error": {"type": "layman_router_stream_error", "message": str(exc)}})
            yield f"event: error\ndata: {error}\n\n".encode("utf-8")
        finally:
            await handle.close()
            terminal = capture.completed_response
            validator = None if terminal is None else terminal.get("status") == "completed"
            outcome = stream_error or error_category or ("completed" if validator else "terminal_usage_missing")
            attempts.append(_usage_attempt(current, terminal, outcome))
            record = _usage_record(
                request_id=request_id, features=features, decision=current, config=config, attempts=attempts,
                latency_ms=int((time.perf_counter() - started) * 1000), fallback_used=fallback_used,
                validator_passed=validator, error_category=stream_error or error_category,
                upstream_request_id=upstream_id,
                optimization=optimization,
                cache_policy=cache_policy,
            )
            await asyncio.to_thread(store.add, record)

    response_headers = provider.response_headers(handle.response.headers)
    response_headers.update(_layman_headers(request_id, current, fallback_used, optimization, cache_policy))
    return StreamingResponse(body(), status_code=200, headers=response_headers, media_type="text/event-stream")


app = create_app()
