from __future__ import annotations

import json
import re

import pytest
from layman_router.tool_output import compact_output, restore_output

from evals.token_optimization.answer_quality import evaluate_json_answer
from evals.token_optimization.log_contract import CASES, SCHEMA


def _reference_fields(text):
    # Independently derive the manually authored answers. Split ONLY the three
    # declared terminators; never strip marker content or treat tabs as endings.
    lines = re.split(r"\r\n|\r|\n", text)
    errors = [(index, match) for index, line in enumerate(lines)
              if (match := re.fullmatch(r"ERROR ([A-Z0-9_]+)(?: expected=(-?\d+) actual=(-?\d+))?", line))]
    assert len(errors) == 2
    index, first = errors[0]
    marker = lines[index - 1]
    assert marker.lstrip(" \t").startswith("checkpoint=")
    exit_line = next(line for line in reversed(lines) if line != "")
    assert re.fullmatch(r"EXIT=-?\d+", exit_line)
    return {
        "first_error": first[1], "second_error": errors[1][1][1],
        "expected": int(first[2]), "actual": int(first[3]),
        "marker": marker, "exit_status": int(exit_line.removeprefix("EXIT=")),
    }


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.case_id)
def test_line_content_contract_has_independent_exact_answers_and_round_trip(case):
    assert _reference_fields(case.text) == case.expected
    packed = compact_output(case.text)
    assert packed != case.text
    restored = restore_output(packed)
    assert restored == case.text
    assert _reference_fields(restored) == case.expected
    assert evaluate_json_answer(json.dumps(case.expected), case.expected, SCHEMA)["passed"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.case_id)
def test_clarified_contract_still_rejects_terminators_and_trimmed_content(case):
    marker = case.expected["marker"]
    candidates = [marker + ending for ending in ("\n", "\r\n", "\r")]
    if marker.strip() != marker:
        candidates.append(marker.strip())
    for wrong_marker in candidates:
        answer = {**case.expected, "marker": wrong_marker}
        report = evaluate_json_answer(json.dumps(answer), case.expected, SCHEMA)
        assert report["parse_ok"] and report["schema_ok"] and not report["passed"]
        assert [key for key, matched in report["field_match"].items() if not matched] == ["marker"]
