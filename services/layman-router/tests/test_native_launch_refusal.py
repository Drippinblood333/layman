from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from layman_router.execution_control import (
    StreamedProcessResult,
    native_execution_error,
)
from layman_router.plus_run import run_plus_task

from evals.token_optimization import benchmark
from evals.token_optimization.cases import CASES

NATIVE_REFUSAL = (
    '2026-10-11T00:00:00Z ERROR codex_core::tools::router: error=exec_command failed: '
    'CreateProcess { message: "UnsupportedOperation(\\"windows unelevated restricted-token '
    'sandbox cannot enforce split writable root sets directly; refusing to run unsandboxed\\")" }'
)
USAGE = {"input_tokens": 10, "output_tokens": 3, "cached_input_tokens": 0, "reasoning_tokens": 0}
EVENTS = "\n".join(json.dumps(event) for event in [
    {"type": "item.completed", "item": {"id": "edit", "type": "file_change"}},
    {"type": "turn.completed", "usage": USAGE},
])


@pytest.mark.parametrize("stderr,expected", [
    (NATIVE_REFUSAL, "windows_sandbox_split_roots_unsupported"),
    ("assistant: " + NATIVE_REFUSAL.split(" ERROR ", 1)[1], None),
    (NATIVE_REFUSAL.replace(" ERROR ", " WARN "), None),
    (NATIVE_REFUSAL.replace("codex_core::tools::router", "other_module"), None),
    (NATIVE_REFUSAL.replace("CreateProcess", "OtherOperation"), None),
    ("sandbox cannot enforce split writable roots", None),
])
def test_native_refusal_requires_observed_router_signature(stderr, expected):
    assert native_execution_error(stderr) == expected


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize("returncode", [0, 1])
def test_launch_refusal_keeps_usage_and_edits_but_never_claims_delivery(
    monkeypatch, tmp_path, streamed, returncode,
):
    monkeypatch.setattr("layman_router.plus_run.codex_login_status", lambda *a, **k: {
        "available": True, "chatgpt_login": True,
    })
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        Path(command[command.index("--output-last-message") + 1]).write_text("edited", encoding="utf-8")
        if streamed:
            return StreamedProcessResult(
                returncode=returncode, stderr=NATIVE_REFUSAL, usage=USAGE, usage_available=True,
                tool_calls=1, unique_files_read=0, compactions=0,
            )
        return subprocess.CompletedProcess(command, returncode, stdout=EVENTS, stderr=NATIVE_REFUSAL)

    if streamed:
        monkeypatch.setattr("layman_router.plus_run.run_streaming_process", runner)
    result = run_plus_task(
        "修复 src/target.py 的顺序", cwd=tmp_path, codex_path=sys.executable,
        **({} if streamed else {"runner": runner}),
    )
    assert result["status"] == "needs_verification"
    assert result["error_category"] == "windows_sandbox_split_roots_unsupported"
    assert result["tool_calls"] == 1
    assert result["command_failures"] == 0
    assert result["usage"] == USAGE
    assert result["usage_incomplete"] is False
    assert result["fallback_used"] is False
    assert len(calls) == 1
    assert "未自动重试或降低权限" in result["answer"]
    assert NATIVE_REFUSAL not in json.dumps(result)


def test_direct_benchmark_uses_same_refusal_gate(monkeypatch, tmp_path):
    monkeypatch.setattr(benchmark.subprocess, "run", lambda command, **kwargs: (
        subprocess.CompletedProcess(command, 0, stdout=EVENTS, stderr=NATIVE_REFUSAL)
    ))
    case = next(case for case in CASES if case.id == "refactor-02")
    result = benchmark._direct_run(case, tmp_path, sys.executable)
    assert result["status"] == "needs_verification"
    assert result["error_category"] == "windows_sandbox_split_roots_unsupported"
    assert result["usage_incomplete"] is False
    assert result["command_failures"] == 0
