from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

# Original implementation of the repeated-log-with-counts strategy described by
# RTK. No upstream Rust source is copied. Every character remains reconstructible.
PREFIX = "Layman lossless lines v1: each JSON [line,count] repeats that exact line count times, in order.\n"
MAX_CHARS = 16 * 1024 * 1024


@dataclass(frozen=True)
class ToolOutputReport:
    mode: str = "off"
    compressed: int = 0
    original_bytes: int = 0
    packed_bytes: int = 0


def compact_output(text: str) -> str:
    """Encode adjacent identical lines only if the serialized UTF-8 text shrinks."""
    if len(text) > MAX_CHARS or text.startswith(PREFIX):
        return text
    if "```" in text:
        return text
    try:
        json.loads(text)
    except (ValueError, RecursionError):
        pass
    else:
        # Structured outputs must remain directly parseable by their consumers.
        return text
    runs: list[list[Any]] = []
    for line in text.splitlines(keepends=True):
        if runs and runs[-1][0] == line:
            runs[-1][1] += 1
        else:
            runs.append([line, 1])
    if not any(count > 1 for _, count in runs):
        return text
    packed = PREFIX + json.dumps(runs, ensure_ascii=False, separators=(",", ":"))
    # JSON escaping matters when this is put inside a Responses request. Require
    # a reduction both as plain text and as a serialized JSON string.
    def size(value: str) -> int:
        return len(value.encode("utf-8"))

    if size(packed) >= size(text) or size(json.dumps(packed, ensure_ascii=False)) >= size(json.dumps(text, ensure_ascii=False)):
        return text
    return packed


def restore_output(text: str) -> str:
    """Restore the exact encoded text; never guess at ordinary output."""
    if not text.startswith(PREFIX):
        return text
    runs = json.loads(text[len(PREFIX):])
    if not isinstance(runs, list):
        # Decode errors use ValueError consistently with json.loads and the CLI.
        raise ValueError("Lossless line output must contain a list")  # noqa: TRY004
    total = 0
    for run in runs:
        if (
            not isinstance(run, list) or len(run) != 2 or not isinstance(run[0], str) or not run[0]
            or isinstance(run[1], bool) or not isinstance(run[1], int) or run[1] < 1
        ):
            raise ValueError("Invalid lossless line run")
        total += len(run[0]) * run[1]
        if total > MAX_CHARS:
            raise ValueError("Restored output exceeds the size limit")
    return "".join(line * count for line, count in runs)


def optimize_tool_outputs(payload: dict[str, Any]) -> tuple[dict[str, Any], ToolOutputReport]:
    """Opt-in transport encoding; never drop a call, an error or an output line."""
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    mode = metadata.get("layman_tool_output_mode", "off")
    if mode not in ("off", "lossless_lines"):
        raise ValueError("layman_tool_output_mode must be 'off' or 'lossless_lines'")
    prepared = deepcopy(payload)
    if mode == "off" or payload.get("model") != "auto" or not isinstance(prepared.get("input"), list):
        return prepared, ToolOutputReport()
    count = original = packed = 0
    for item in prepared["input"]:
        if not isinstance(item, dict) or item.get("type") != "function_call_output" or not isinstance(item.get("output"), str):
            continue
        text = item["output"]
        compacted = compact_output(text)
        original += len(text.encode("utf-8"))
        packed += len(compacted.encode("utf-8"))
        count += int(text != compacted)
        item["output"] = compacted
    return prepared, ToolOutputReport(mode="lossless_lines", compressed=count, original_bytes=original, packed_bytes=packed)
