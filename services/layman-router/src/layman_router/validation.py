from __future__ import annotations

import json
from typing import Any

from jsonschema import ValidationError, validate

from .models import ValidationResult


def output_text(response: dict[str, Any]) -> str:
    pieces: list[str] = []
    for item in response.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "output_text" and isinstance(content.get("text"), str):
                pieces.append(content["text"])
    return "".join(pieces)


def validate_response(response: dict[str, Any], request_payload: dict[str, Any]) -> ValidationResult:
    if response.get("status") == "incomplete":
        return ValidationResult(passed=False, reason="incomplete response")
    output = response.get("output")
    if not isinstance(output, list) or not output:
        return ValidationResult(passed=False, reason="empty output")

    text_config = request_payload.get("text")
    format_config = text_config.get("format") if isinstance(text_config, dict) else None
    schema = format_config.get("schema") if isinstance(format_config, dict) and format_config.get("type") == "json_schema" else None
    if schema:
        text = output_text(response)
        if not text:
            return ValidationResult(passed=False, reason="structured output is empty")
        try:
            value = json.loads(text)
            validate(value, schema)
        except (json.JSONDecodeError, ValidationError) as exc:
            return ValidationResult(passed=False, reason=f"json schema validation failed: {exc.message if isinstance(exc, ValidationError) else exc}")
    return ValidationResult(passed=True)
