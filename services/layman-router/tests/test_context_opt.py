from __future__ import annotations

from layman_router.context_opt import optimize_payload


LONG = "重复的历史说明。" * 40


def test_safe_mode_removes_only_older_exact_duplicate():
    payload = {
        "model": "auto",
        "metadata": {"layman_context_mode": "safe"},
        "input": [
            {"role": "user", "content": LONG},
            {"role": "assistant", "content": "ack"},
            {"role": "user", "content": LONG},
            {"role": "user", "content": "当前任务不能删除"},
        ],
    }
    optimized, report = optimize_payload(payload)
    assert report.duplicate_blocks_removed == 1
    assert report.optimized_chars < report.original_chars
    assert [item["content"] for item in optimized["input"]] == ["ack", LONG, "当前任务不能删除"]
    assert payload["input"][0]["content"] == LONG


def test_default_and_explicit_models_are_unchanged():
    payload = {"model": "auto", "input": [{"role": "user", "content": LONG}, {"role": "assistant", "content": LONG}]}
    optimized, report = optimize_payload(payload)
    assert optimized == payload
    assert report.mode == "off"

    explicit = {**payload, "model": "gpt-5.6-sol", "metadata": {"layman_context_mode": "safe"}}
    optimized, report = optimize_payload(explicit)
    assert optimized == explicit
    assert report.mode == "off"


def test_current_user_code_and_tool_content_are_preserved():
    code = "```python\n" + LONG + "\n```"
    payload = {
        "model": "auto",
        "metadata": {"layman_context_mode": "safe"},
        "input": [
            {"role": "assistant", "content": code},
            {"role": "assistant", "content": code},
            {"type": "function_call_output", "call_id": "call_1", "output": LONG},
            {"role": "user", "content": LONG},
        ],
    }
    optimized, report = optimize_payload(payload)
    assert optimized == payload
    assert report.duplicate_blocks_removed == 0


def test_unicode_and_newline_normalization_are_safe():
    first = ("中文上下文\r\n" * 40) + "结束"
    second = first.replace("\r\n", "\n")
    payload = {
        "model": "auto",
        "metadata": {"layman_context_mode": "safe"},
        "input": [
            {"role": "assistant", "content": [{"type": "output_text", "text": first}]},
            {"role": "assistant", "content": [{"type": "output_text", "text": second}]},
            {"role": "user", "content": "继续"},
        ],
    }
    optimized, report = optimize_payload(payload)
    assert report.duplicate_blocks_removed == 1
    assert len(optimized["input"]) == 2
