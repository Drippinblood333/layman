"""Fixed-field answer diagnostics for preregistered synthetic evaluations only."""
from __future__ import annotations

import json
from typing import Any

import jsonschema


def evaluate_json_answer(text: str, expected: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Retain booleans and declared field names, never values or validator errors.

    Expected keys must be public, fixed fixture labels, not user-derived names.
    The acceptance rule remains schema validation plus exact expected equality.
    An invalid judge schema raises rather than being blamed on a model answer.
    """
    validator_type = jsonschema.validators.validator_for(schema)
    validator_type.check_schema(schema)
    report: dict[str, Any] = {
        "parse_ok": False, "schema_ok": False,
        "field_match": dict.fromkeys(expected, False), "passed": False,
    }
    try:
        value = json.loads(text)
    except (ValueError, RecursionError):
        return report
    report["parse_ok"] = True
    if isinstance(value, dict):
        report["field_match"] = {key: key in value and value[key] == target for key, target in expected.items()}
    try:
        validator_type(schema).validate(value)
    except jsonschema.ValidationError:
        return report
    report["schema_ok"] = True
    report["passed"] = value == expected
    return report
