"""Offline, synthetic lossless-output measurements; no model or billable calls."""
from __future__ import annotations

import json

from layman_router.tool_output import compact_output, restore_output


def main() -> int:
    cases = {
        "repeated_progress": "progress: waiting for worker\n" * 100 + "done\n",
        "repeated_warning_with_failure": "warning: deprecated option\n" * 100 + "FAILED: assertion expected 2 got 1\n",
        "chinese_crlf": "进度：等待工作进程\r\n" * 100 + "失败：保留这条诊断\r\n",
        "unique_test_results": "".join(f"test_{index}: PASSED\n" for index in range(100)),
        "short_repeat": "ok\nok\n",
        "structured_json": json.dumps(["same"] * 100, indent=2),
        "fenced_code": "```python\n" + "print('same')\n" * 100 + "```",
        "failure_traceback": "Traceback (most recent call last):\n  synthetic_fixture.py:10\nAssertionError: expected 2 got 1\n",
    }
    rows = []
    for name, raw in cases.items():
        packed = compact_output(raw)
        assert restore_output(packed) == raw, f"Lossless round trip failed: {name}"
        original = len(raw.encode("utf-8"))
        encoded = len(packed.encode("utf-8"))
        assert encoded <= original, f"Output grew: {name}"
        rows.append({
            "case": name, "original_utf8_bytes": original, "packed_utf8_bytes": encoded,
            "byte_reduction_pct": round(100 * (original - encoded) / original, 2),
            "round_trip_exact": True,
        })
    print(json.dumps({
        "measurement": "synthetic_utf8_bytes_not_model_tokens",
        "model_calls": 0,
        "measured_task_token_savings": None,
        "cases": rows,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
