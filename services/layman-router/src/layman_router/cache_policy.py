from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


CONTROL_METADATA_PREFIX = "layman_"
CACHE_MODE_METADATA = "layman_prompt_cache"
CACHE_KEY_METADATA = "layman_prompt_cache_key"
SUPPORTED_CACHE_BLOCKS = {"input_text", "input_image", "input_file"}


@dataclass(frozen=True)
class PromptCachePolicy:
    """The non-sensitive cache policy Layman applied to an upstream request."""

    mode: str = "off"
    breakpoints: int = 0


def _content_breakpoints(value: Any) -> int:
    if not isinstance(value, list):
        return 0
    count = 0
    for message in value:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") not in SUPPORTED_CACHE_BLOCKS:
                continue
            if block.get("prompt_cache_breakpoint") == {"mode": "explicit"}:
                count += 1
    return count


def _strip_control_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    prepared = deepcopy(payload)
    metadata = prepared.get("metadata")
    if not isinstance(metadata, dict):
        return prepared
    forwarded = {key: value for key, value in metadata.items() if not str(key).startswith(CONTROL_METADATA_PREFIX)}
    if forwarded:
        prepared["metadata"] = forwarded
    else:
        prepared.pop("metadata", None)
    return prepared


def prepare_upstream_payload(payload: dict[str, Any], *, automatic: bool, selected_model: str) -> tuple[dict[str, Any], PromptCachePolicy]:
    """Remove router-only metadata and apply an explicit cache policy when requested.

    Layman deliberately never guesses which part of an application prompt is
    stable. A caller must mark one or more supported content blocks and opt in
    with a non-secret cache key. This avoids billable cache writes for changing
    conversation suffixes.
    """

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    requested_mode = metadata.get(CACHE_MODE_METADATA)
    cache_key = metadata.get(CACHE_KEY_METADATA)
    prepared = _strip_control_metadata(payload)

    if requested_mode in {None, "off"}:
        return prepared, PromptCachePolicy()
    if requested_mode != "explicit":
        raise ValueError("layman_prompt_cache must be 'explicit' or 'off'")
    if not automatic or not selected_model.startswith("gpt-5.6"):
        raise ValueError("layman_prompt_cache=explicit is available only for automatic GPT-5.6 routes")
    if not isinstance(cache_key, str) or not cache_key.strip():
        raise ValueError("layman_prompt_cache_key must be a non-empty string")
    if "prompt_cache_key" in prepared or "prompt_cache_options" in prepared:
        raise ValueError("Use either Layman cache metadata or native prompt_cache_* fields, not both")

    breakpoints = _content_breakpoints(prepared.get("input"))
    if breakpoints == 0:
        raise ValueError(
            "layman_prompt_cache=explicit requires an input_text, input_image, or input_file block with "
            "prompt_cache_breakpoint: {mode: 'explicit'}"
        )

    prepared["prompt_cache_key"] = cache_key.strip()
    prepared["prompt_cache_options"] = {"mode": "explicit", "ttl": "30m"}
    return prepared, PromptCachePolicy(mode="explicit", breakpoints=breakpoints)
