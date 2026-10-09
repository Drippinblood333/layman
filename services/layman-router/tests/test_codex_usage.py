from __future__ import annotations

import json
import subprocess

import pytest
from layman_router.execution_control import (
    EventBudgetTracker,
    process_launch_options,
    usage_from_events,
)
from layman_router.plus_eval import _usage_from_events
from layman_router.plus_run import _usage_available


def parse_both(events):
    lines = [json.dumps(event) for event in events]
    tracker = EventBudgetTracker()
    for line in lines:
        tracker.consume(line)
    buffered, available = usage_from_events("\n".join(lines))
    assert tracker.usage == buffered == _usage_from_events("\n".join(lines))
    assert tracker.usage_available == available == _usage_available("\n".join(lines))
    return buffered, available


def test_tool_usage_cannot_override_authoritative_completed_turn():
    fake = {"input_tokens": 999999, "output_tokens": 8888}
    real = {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 10, "reasoning_output_tokens": 4}
    events = [
        {"type": "item.completed", "item": {"type": "mcp_tool_call", "result": {"usage": fake}}},
        {"type": "turn.completed", "usage": real},
        {"type": "item.completed", "item": {"type": "agent_message", "usage": fake}},
    ]
    usage, available = parse_both(events)
    assert available
    assert usage == {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 10, "reasoning_tokens": 4}


@pytest.mark.parametrize("event", [
    {"input_tokens": 100, "output_tokens": 10},
    {"type": "item.completed", "usage": {"input_tokens": 100, "output_tokens": 10}},
    {"type": "turn.failed", "usage": {"input_tokens": 100, "output_tokens": 10}},
    {"type": "turn.completed", "usage": {"input_tokens": 100}},
    {"type": "turn.completed", "usage": {"input_tokens": True, "output_tokens": 10}},
    {"type": "turn.completed", "usage": {"input_tokens": -1, "output_tokens": 10}},
    {"type": "turn.completed", "usage": {"input_tokens": "100", "output_tokens": 10}},
    {"type": "turn.completed", "usage": {"input_tokens": 1.0, "output_tokens": 10}},
    {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": False}},
    {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 10, "cached_input_tokens": 101}},
    {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 10, "reasoning_output_tokens": -1}},
    {"type": "turn.completed", "usage": []},
    [{"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 10}}],
])
def test_missing_or_untrusted_usage_is_not_available(event):
    usage, available = parse_both([event])
    assert not available
    assert all(value == 0 for value in usage.values())


def test_multiple_completed_turns_sum_without_double_counting_cached_input():
    usage, available = parse_both([
        {"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 10}},
        {"type": "turn.completed", "usage": {"input_tokens": 30, "cached_tokens": 20, "output_tokens": 5}},
    ])
    assert available
    assert usage == {"input_tokens": 130, "cached_input_tokens": 100, "output_tokens": 15, "reasoning_tokens": 0}


def test_zero_usage_and_invalid_json_have_distinct_availability():
    usage, available = parse_both([{"type": "turn.completed", "usage": {"input_tokens": 0, "output_tokens": 0}}])
    assert available
    assert all(value == 0 for value in usage.values())
    assert usage_from_events("invalid json\n") == (usage, False)


@pytest.mark.parametrize("platform_name", ["nt", "posix"])
def test_launch_options_match_streamed_and_direct_process_isolation(platform_name):
    expected = {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)} if platform_name == "nt" else {"start_new_session": True}
    assert process_launch_options(platform_name) == expected
