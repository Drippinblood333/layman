from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


MIN_DUPLICATE_CHARS = 200
TEXT_ITEM_TYPES = {"input_text", "output_text", "text"}


@dataclass(frozen=True)
class ContextOptimization:
    mode: str
    original_chars: int
    optimized_chars: int
    duplicate_blocks_removed: int

    @property
    def changed(self) -> bool:
        return self.duplicate_blocks_removed > 0


def _serialized_chars(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))


def _normalized(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _safe_text(text: str) -> bool:
    return len(text) >= MIN_DUPLICATE_CHARS and "```" not in text


def _message_text_items(message: dict[str, Any]) -> list[tuple[int | None, str]]:
    content = message.get("content")
    if isinstance(content, str):
        return [(None, content)]
    if not isinstance(content, list):
        return []
    items: list[tuple[int | None, str]] = []
    for index, item in enumerate(content):
        if not isinstance(item, dict) or item.get("type") not in TEXT_ITEM_TYPES:
            continue
        text = item.get("text")
        if isinstance(text, str):
            items.append((index, text))
    return items


def _last_user_index(messages: list[Any]) -> int | None:
    for index in range(len(messages) - 1, -1, -1):
        item = messages[index]
        if isinstance(item, dict) and item.get("role") == "user":
            return index
    return None


def optimize_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], ContextOptimization]:
    """Remove only exact, old prose duplicates from an explicitly opted-in auto request."""

    original_chars = _serialized_chars(payload)
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    mode = str(metadata.get("layman_context_mode") or "off")
    if payload.get("model") != "auto" or mode != "safe" or not isinstance(payload.get("input"), list):
        return deepcopy(payload), ContextOptimization(mode="off", original_chars=original_chars, optimized_chars=original_chars, duplicate_blocks_removed=0)

    optimized = deepcopy(payload)
    messages = optimized["input"]
    last_user = _last_user_index(messages)
    seen: set[str] = set()
    removed = 0

    for message_index in range(len(messages) - 1, -1, -1):
        message = messages[message_index]
        if not isinstance(message, dict) or message.get("role") not in {"user", "assistant"}:
            continue
        text_items = _message_text_items(message)
        removable_indexes: set[int] = set()
        remove_string_content = False
        for content_index, text in reversed(text_items):
            normalized = _normalized(text)
            eligible = _safe_text(normalized) and message_index != last_user
            if eligible and normalized in seen:
                if content_index is None:
                    remove_string_content = True
                else:
                    removable_indexes.add(content_index)
                removed += 1
            elif _safe_text(normalized):
                seen.add(normalized)
        if remove_string_content:
            message["content"] = ""
        elif removable_indexes and isinstance(message.get("content"), list):
            message["content"] = [item for index, item in enumerate(message["content"]) if index not in removable_indexes]

    optimized["input"] = [
        message
        for message in messages
        if not (
            isinstance(message, dict)
            and message.get("role") in {"user", "assistant"}
            and (message.get("content") == "" or message.get("content") == [])
        )
    ]
    optimized_chars = _serialized_chars(optimized)
    return optimized, ContextOptimization(
        mode="safe",
        original_chars=original_chars,
        optimized_chars=optimized_chars,
        duplicate_blocks_removed=removed,
    )
