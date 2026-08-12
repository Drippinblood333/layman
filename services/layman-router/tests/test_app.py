from __future__ import annotations

import json

import httpx
import pytest

import layman_router.app as app_module
from layman_router.app import create_app
from layman_router.telemetry import estimate_cost, extract_usage


class ChunkStream(httpx.AsyncByteStream):
    def __init__(self, chunks, *, fail_after: bool = False):
        self.chunks = chunks
        self.fail_after = fail_after

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk
        if self.fail_after:
            raise httpx.ReadError("interrupted")


def response_body(model: str = "gpt-5.6-luna"):
    return {
        "id": "resp_test",
        "status": "completed",
        "model": model,
        "output": [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}],
        "usage": {
            "input_tokens": 100,
            "input_tokens_details": {"cached_tokens": 20},
            "output_tokens": 10,
            "output_tokens_details": {"reasoning_tokens": 2},
        },
    }


@pytest.mark.asyncio
async def test_auto_routes_and_preserves_fields(router_config):
    seen = []

    async def upstream(request: httpx.Request):
        payload = json.loads(request.content)
        seen.append(payload)
        return httpx.Response(200, json=response_body(payload["model"]), headers={"openai-request-id": "upstream-one"})

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post("/v1/responses", headers={"Authorization": "Bearer test-secret"}, json={
            "model": "auto", "input": "请总结这段内容", "previous_response_id": "resp_old",
            "tools": [{"type": "function", "name": "read"}], "tool_choice": "auto",
        })
    assert result.status_code == 200
    assert result.headers["x-layman-route-tier"] == "fast"
    assert result.headers["x-layman-validator-passed"] == "true"
    assert seen[0]["model"] == "gpt-5.6-luna"
    assert seen[0]["previous_response_id"] == "resp_old"
    assert seen[0]["tools"][0]["name"] == "read"


@pytest.mark.asyncio
async def test_safe_context_mode_deduplicates_before_upstream(router_config):
    seen = []
    repeated = "同一段较长的历史上下文。" * 30

    async def upstream(request: httpx.Request):
        payload = json.loads(request.content)
        seen.append(payload)
        return httpx.Response(200, json=response_body(payload["model"]))

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post(
            "/v1/responses",
            headers={"Authorization": "Bearer secret"},
            json={
                "model": "auto",
                "metadata": {"layman_context_mode": "safe"},
                "input": [
                    {"role": "assistant", "content": repeated},
                    {"role": "assistant", "content": repeated},
                    {"role": "user", "content": "请总结"},
                ],
            },
        )
    assert result.status_code == 200
    assert result.headers["x-layman-context-mode"] == "safe"
    assert result.headers["x-layman-context-duplicates-removed"] == "1"
    assert len(seen[0]["input"]) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("reasoning", "high", "reasoning must be an object"),
        ("max_output_tokens", "100", "max_output_tokens must be a positive integer"),
        ("max_output_tokens", 0, "max_output_tokens must be a positive integer"),
    ],
)
async def test_invalid_policy_fields_return_400(router_config, field, value, message):
    app = create_app(router_config, transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post(
            "/v1/responses",
            headers={"Authorization": "Bearer secret"},
            json={"model": "auto", "input": "hello", field: value},
        )
    assert result.status_code == 400
    assert result.json()["detail"] == message


@pytest.mark.asyncio
async def test_safe_context_mode_is_applied_before_classification(router_config, monkeypatch):
    repeated = "同一段较长的历史上下文。" * 30
    classified = []
    original_classify = app_module.classify_task

    def observe(payload, settings):
        classified.append(payload)
        return original_classify(payload, settings)

    monkeypatch.setattr(app_module, "classify_task", observe)
    app = create_app(
        router_config,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=response_body(json.loads(request.content)["model"]))
        ),
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post(
            "/v1/responses",
            headers={"Authorization": "Bearer secret"},
            json={
                "model": "auto",
                "metadata": {"layman_context_mode": "safe"},
                "input": [
                    {"role": "assistant", "content": repeated},
                    {"role": "assistant", "content": repeated},
                    {"role": "user", "content": "请检查生产支付风险"},
                ],
            },
        )
    assert result.status_code == 200
    assert len(classified[0]["input"]) == 2
    assert classified[0]["input"][-1]["content"] == "请检查生产支付风险"


@pytest.mark.asyncio
async def test_explicit_prompt_cache_is_forwarded_only_when_the_prefix_is_marked(router_config):
    seen = []

    async def upstream(request: httpx.Request):
        payload = json.loads(request.content)
        seen.append(payload)
        return httpx.Response(200, json=response_body(payload["model"]))

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post(
            "/v1/responses",
            headers={"Authorization": "Bearer secret"},
            json={
                "model": "auto",
                "metadata": {"layman_prompt_cache": "explicit", "layman_prompt_cache_key": "stable-docs"},
                "input": [{"role": "user", "content": [
                    {"type": "input_text", "text": "stable", "prompt_cache_breakpoint": {"mode": "explicit"}},
                    {"type": "input_text", "text": "current"},
                ]}],
            },
        )
    assert result.status_code == 200
    assert result.headers["x-layman-prompt-cache-mode"] == "explicit"
    assert seen[0]["prompt_cache_key"] == "stable-docs"
    assert seen[0]["prompt_cache_options"] == {"mode": "explicit", "ttl": "30m"}
    assert "metadata" not in seen[0]


@pytest.mark.asyncio
async def test_explicit_prompt_cache_requires_a_marked_prefix(router_config):
    app = create_app(router_config, transport=httpx.MockTransport(lambda _request: pytest.fail("upstream must not be called")))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post(
            "/v1/responses",
            headers={"Authorization": "Bearer secret"},
            json={"model": "auto", "input": "hello", "metadata": {"layman_prompt_cache": "explicit", "layman_prompt_cache_key": "stable"}},
        )
    assert result.status_code == 400


@pytest.mark.asyncio
async def test_explicit_model_passes_through(router_config):
    seen = []

    async def upstream(request: httpx.Request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=response_body("custom-model"))

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post("/v1/responses", headers={"Authorization": "Bearer secret"}, json={"model": "custom-model", "input": "hello", "reasoning": {"effort": "low"}})
    assert result.status_code == 200
    assert seen == [{"model": "custom-model", "input": "hello", "reasoning": {"effort": "low"}}]
    recent = app.state.store.recent()[0]
    assert recent["automatic"] is False
    assert recent["cost_estimate_available"] is False
    assert recent["unpriced_attempts"] == 1
    summary = app.state.store.summary()
    assert summary["automatic_requests"] == 0
    assert summary["unpriced_requests"] == 1
    assert summary["estimated_savings_usd"] == 0
    assert summary["total_cost_is_partial"] is True


@pytest.mark.asyncio
async def test_retryable_error_falls_back_once(router_config):
    seen = []

    async def upstream(request: httpx.Request):
        payload = json.loads(request.content)
        seen.append(payload["model"])
        if len(seen) == 1:
            return httpx.Response(503, json={"error": {"message": "temporary"}})
        return httpx.Response(200, json=response_body(payload["model"]))

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post("/v1/responses", headers={"Authorization": "Bearer secret"}, json={"model": "auto", "input": "总结"})
    assert result.status_code == 200
    assert seen == ["gpt-5.6-luna", "gpt-5.6-terra"]
    assert result.headers["x-layman-fallback-used"] == "true"
    recent = app.state.store.recent()[0]
    assert recent["attempt_count"] == 2
    assert recent["input_tokens"] == 100
    assert recent["usage_incomplete"] is True
    assert [attempt["usage_available"] for attempt in recent["attempts"]] == [False, True]


@pytest.mark.asyncio
async def test_validation_fallback_accumulates_and_prices_each_attempt(router_config):
    calls = []
    first = response_body("gpt-5.6-luna")
    first["status"] = "incomplete"
    second = response_body("gpt-5.6-terra")
    for response in (first, second):
        response["usage"]["input_tokens"] = 200_000
        response["usage"]["input_tokens_details"]["cached_tokens"] = 20_000

    async def upstream(request: httpx.Request):
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(200, json=first if len(calls) == 1 else second)

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post(
            "/v1/responses", headers={"Authorization": "Bearer secret"}, json={"model": "auto", "input": "总结"}
        )
    assert result.status_code == 200
    recent = app.state.store.recent()[0]
    expected = estimate_cost(extract_usage(first), router_config.tiers["fast"].pricing) + estimate_cost(
        extract_usage(second), router_config.tiers["balanced"].pricing
    )
    assert recent["input_tokens"] == 400_000
    assert recent["output_tokens"] == 20
    assert recent["estimated_cost_usd"] == round(expected, 9)
    expected_baseline = sum(
        estimate_cost(extract_usage(response), router_config.tiers["deep"].pricing) for response in (first, second)
    )
    assert recent["estimated_always_deep_cost_usd"] == round(expected_baseline, 9)
    assert recent["usage_incomplete"] is False
    assert [attempt["selected_model"] for attempt in recent["attempts"]] == calls


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [429, 500, 503])
async def test_all_retryable_http_statuses_fall_back_once(router_config, status):
    calls = []

    async def upstream(request: httpx.Request):
        payload = json.loads(request.content)
        calls.append(payload["model"])
        if len(calls) == 1:
            return httpx.Response(status, json={"error": {"message": "retry"}})
        return httpx.Response(200, json=response_body(payload["model"]))

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post("/v1/responses", headers={"Authorization": "Bearer secret"}, json={"model": "auto", "input": "总结"})
    assert result.status_code == 200
    assert calls == ["gpt-5.6-luna", "gpt-5.6-terra"]


@pytest.mark.asyncio
async def test_transport_timeout_falls_back_once(router_config):
    calls = []

    async def upstream(request: httpx.Request):
        payload = json.loads(request.content)
        calls.append(payload["model"])
        if len(calls) == 1:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json=response_body(payload["model"]))

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post("/v1/responses", headers={"Authorization": "Bearer secret"}, json={"model": "auto", "input": "总结"})
    assert result.status_code == 200
    assert result.headers["x-layman-fallback-used"] == "true"


@pytest.mark.asyncio
async def test_streaming_is_forwarded_in_order(router_config):
    terminal = response_body("gpt-5.6-luna")
    body = (
        b'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"hi"}\n\n'
        + f'event: response.completed\ndata: {json.dumps({"type": "response.completed", "response": terminal})}\n\n'.encode()
    )

    async def upstream(_request: httpx.Request):
        return httpx.Response(200, stream=ChunkStream([body]), headers={"content-type": "text/event-stream"})

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post("/v1/responses", headers={"Authorization": "Bearer secret"}, json={"model": "auto", "input": "总结", "stream": True})
    assert result.status_code == 200
    assert result.content == body


@pytest.mark.asyncio
async def test_streaming_prefetches_one_complete_sse_event(router_config):
    first = b'event: response.output_text.delta\ndata: {"type":"response.output_text.delta",'
    second = b'"delta":"hi"}\n\n'
    terminal = response_body("gpt-5.6-luna")
    last = f'event: response.completed\ndata: {json.dumps({"type": "response.completed", "response": terminal})}\n\n'.encode()

    async def upstream(_request: httpx.Request):
        return httpx.Response(200, stream=ChunkStream([first, second, last]), headers={"content-type": "text/event-stream"})

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post("/v1/responses", headers={"Authorization": "Bearer secret"}, json={"model": "auto", "input": "总结", "stream": True})
    assert result.content == first + second + last


@pytest.mark.asyncio
async def test_stream_retry_before_first_event(router_config):
    calls = []
    terminal = response_body("gpt-5.6-terra")
    success = f'event: response.completed\ndata: {json.dumps({"type": "response.completed", "response": terminal})}\n\n'.encode()

    async def upstream(request: httpx.Request):
        calls.append(json.loads(request.content)["model"])
        if len(calls) == 1:
            return httpx.Response(503, stream=ChunkStream([b'{"error":"temporary"}']))
        return httpx.Response(200, stream=ChunkStream([success]), headers={"content-type": "text/event-stream"})

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post("/v1/responses", headers={"Authorization": "Bearer secret"}, json={"model": "auto", "input": "总结", "stream": True})
    assert result.status_code == 200
    assert calls == ["gpt-5.6-luna", "gpt-5.6-terra"]
    assert result.content == success
    recent = app.state.store.recent()[0]
    assert recent["attempt_count"] == 2
    assert recent["input_tokens"] == 100
    assert recent["usage_incomplete"] is True


@pytest.mark.asyncio
async def test_empty_stream_falls_back_before_forwarding(router_config):
    calls = []
    terminal = response_body("gpt-5.6-terra")
    success = f'event: response.completed\ndata: {json.dumps({"type": "response.completed", "response": terminal})}\n\n'.encode()

    async def upstream(request: httpx.Request):
        calls.append(json.loads(request.content)["model"])
        if len(calls) == 1:
            return httpx.Response(200, stream=ChunkStream([]), headers={"content-type": "text/event-stream"})
        return httpx.Response(200, stream=ChunkStream([success]), headers={"content-type": "text/event-stream"})

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post("/v1/responses", headers={"Authorization": "Bearer secret"}, json={"model": "auto", "input": "总结", "stream": True})
    assert result.status_code == 200
    assert calls == ["gpt-5.6-luna", "gpt-5.6-terra"]
    assert result.content == success


@pytest.mark.asyncio
async def test_stream_interruption_after_first_event_is_not_retried(router_config):
    calls = 0
    first = b'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"partial"}\n\n'

    async def upstream(_request: httpx.Request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, stream=ChunkStream([first], fail_after=True), headers={"content-type": "text/event-stream"})

    app = create_app(router_config, transport=httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post("/v1/responses", headers={"Authorization": "Bearer secret"}, json={"model": "auto", "input": "总结", "stream": True})
    assert calls == 1
    assert result.content.startswith(first)
    assert b"layman_router_stream_error" in result.content


@pytest.mark.asyncio
async def test_admin_summary_is_loopback_and_token_guarded(router_config, monkeypatch):
    monkeypatch.setenv(router_config.admin_token_env, "admin-secret")
    app = create_app(router_config, transport=httpx.MockTransport(lambda _request: httpx.Response(500)))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.get("/admin/usage/summary")
        allowed = await client.get("/admin/usage/summary", headers={"X-Layman-Admin-Token": "admin-secret"})
    assert denied.status_code == 401
    assert allowed.status_code == 200
    assert "estimated_savings_usd" in allowed.json()
    assert "validator_pass_rate" in allowed.json()


@pytest.mark.asyncio
async def test_dashboard_is_public_shell_but_data_requires_token(router_config, monkeypatch):
    monkeypatch.setenv(router_config.admin_token_env, "admin-secret")
    app = create_app(router_config, transport=httpx.MockTransport(lambda _request: httpx.Response(500)))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        dashboard = await client.get("/admin/")
        dashboard_script = await client.get("/admin/assets/dashboard.js")
        denied = await client.get("/admin/usage/recent")
        allowed = await client.get("/admin/usage/recent", headers={"X-Layman-Admin-Token": "admin-secret"})
    assert dashboard.status_code == 200
    assert "Layman Router Control Room" in dashboard.text
    assert 'id="measurementNote"' in dashboard.text
    assert "LAYMAN ROUTER v1.0" in dashboard.text
    assert "estimated_automatic_cost_usd" in dashboard_script.text
    assert "UNPRICED" in dashboard_script.text
    assert "frame-ancestors 'none'" in dashboard.headers["content-security-policy"]
    assert denied.status_code == 401
    assert allowed.json() == {"requests": []}


@pytest.mark.asyncio
async def test_authorization_is_required(router_config):
    app = create_app(router_config, transport=httpx.MockTransport(lambda _request: httpx.Response(200)))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post("/v1/responses", json={"model": "auto", "input": "hello"})
    assert result.status_code == 401


@pytest.mark.asyncio
async def test_demo_mode_cannot_forward_responses(router_config):
    router_config.demo_mode = True
    app = create_app(router_config, transport=httpx.MockTransport(lambda _request: pytest.fail("upstream must not be called")))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.post("/v1/responses", headers={"Authorization": "Bearer secret"}, json={"model": "auto", "input": "hello"})
    assert result.status_code == 403
