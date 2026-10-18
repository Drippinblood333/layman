from __future__ import annotations

import json

import jsonschema
import pytest

from evals.token_optimization.answer_quality import evaluate_json_answer

EXPECTED = {"code": "synthetic-secret-sentinel", "count": 3}
SCHEMA = {
    "type": "object", "properties": {"code": {"type": "string"}, "count": {"type": "integer"}},
    "required": ["code", "count"], "additionalProperties": False,
}


@pytest.mark.parametrize("value,parse_ok,schema_ok,fields,passed", [
    ("not json", False, False, {"code": False, "count": False}, False),
    ("[]", True, False, {"code": False, "count": False}, False),
    (json.dumps(EXPECTED), True, True, {"code": True, "count": True}, True),
    (json.dumps({**EXPECTED, "count": 4}), True, True, {"code": True, "count": False}, False),
    (json.dumps({**EXPECTED, "code": "wrong"}), True, True, {"code": False, "count": True}, False),
    (json.dumps({"code": EXPECTED["code"]}), True, False, {"code": True, "count": False}, False),
    (json.dumps({**EXPECTED, "count": True}), True, False, {"code": True, "count": False}, False),
    (json.dumps({**EXPECTED, "extra": "private"}), True, False, {"code": True, "count": True}, False),
])
def test_answer_diagnostics_preserve_gate_without_retaining_values(value, parse_ok, schema_ok, fields, passed):
    report = evaluate_json_answer(value, EXPECTED, SCHEMA)
    assert report == {"parse_ok": parse_ok, "schema_ok": schema_ok, "field_match": fields, "passed": passed}
    assert EXPECTED["code"] not in json.dumps(report)
    assert "private" not in json.dumps(report)


@pytest.mark.parametrize("answer", [json.dumps(EXPECTED), "not json"])
def test_invalid_judge_schema_is_not_reported_as_model_failure(answer):
    with pytest.raises(jsonschema.SchemaError):
        evaluate_json_answer(answer, EXPECTED, {"type": "invalid-schema-type"})
