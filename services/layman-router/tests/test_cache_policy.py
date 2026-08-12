from __future__ import annotations

import pytest

from layman_router.cache_policy import prepare_upstream_payload


def explicit_prefix():
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "stable project instructions",
                    "prompt_cache_breakpoint": {"mode": "explicit"},
                },
                {"type": "input_text", "text": "current question"},
            ],
        }
    ]


def test_explicit_cache_is_opt_in_and_does_not_forward_layman_metadata():
    payload = {
        "model": "auto",
        "input": explicit_prefix(),
        "metadata": {
            "customer_label": "visible-upstream",
            "layman_prompt_cache": "explicit",
            "layman_prompt_cache_key": "docs-v1",
            "layman_route": "balanced",
            "layman_project_id": "internal",
        },
    }
    prepared, policy = prepare_upstream_payload(payload, automatic=True, selected_model="gpt-5.6-terra")
    assert policy.mode == "explicit"
    assert policy.breakpoints == 1
    assert prepared["prompt_cache_key"] == "docs-v1"
    assert prepared["prompt_cache_options"] == {"mode": "explicit", "ttl": "30m"}
    assert prepared["metadata"] == {"customer_label": "visible-upstream"}
    assert payload["metadata"]["layman_route"] == "balanced"


def test_router_control_metadata_is_not_sent_upstream_when_cache_is_off():
    payload = {"model": "auto", "input": "hello", "metadata": {"layman_route": "fast", "note": "keep"}}
    prepared, policy = prepare_upstream_payload(payload, automatic=True, selected_model="gpt-5.6-luna")
    assert policy.mode == "off"
    assert prepared["metadata"] == {"note": "keep"}


@pytest.mark.parametrize(
    ("payload", "automatic", "model", "message"),
    [
        ({"model": "auto", "input": explicit_prefix(), "metadata": {"layman_prompt_cache": "explicit"}}, True, "gpt-5.6-luna", "cache_key"),
        ({"model": "auto", "input": "hello", "metadata": {"layman_prompt_cache": "explicit", "layman_prompt_cache_key": "key"}}, True, "gpt-5.6-luna", "requires"),
        ({"model": "gpt-5.6-sol", "input": explicit_prefix(), "metadata": {"layman_prompt_cache": "explicit", "layman_prompt_cache_key": "key"}}, False, "gpt-5.6-sol", "automatic"),
        ({"model": "auto", "input": explicit_prefix(), "prompt_cache_key": "native", "metadata": {"layman_prompt_cache": "explicit", "layman_prompt_cache_key": "key"}}, True, "gpt-5.6-terra", "either"),
    ],
)
def test_explicit_cache_rejects_ambiguous_or_unsupported_requests(payload, automatic, model, message):
    with pytest.raises(ValueError, match=message):
        prepare_upstream_payload(payload, automatic=automatic, selected_model=model)
