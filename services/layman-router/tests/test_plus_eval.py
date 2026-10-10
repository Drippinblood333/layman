from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from layman_router import plus_eval
from layman_router.plus_eval import (
    PlusEvalArm,
    build_plan,
    codex_login_status,
    completed_keys,
    event_metrics,
    experiment_fingerprint,
    find_codex,
    load_cases,
    run_arm,
    run_plus_eval,
)


def test_buffered_event_metrics_deduplicate_started_and_completed_operations():
    item = {"id": "cmd-1", "type": "command_execution", "command": "Get-Content src/target.py"}
    events = "\n".join(json.dumps({"type": kind, "item": item}) for kind in ("item.started", "item.completed"))
    assert event_metrics(events) == {"tool_calls": 1, "unique_files_read": 1, "compactions": 0}


def test_release_plan_is_eighteen_cases_and_thirty_six_calls(router_config):
    plan = build_plan(load_cases(), config=router_config)
    assert len(load_cases()) == 18
    assert len(plan) == 36
    assert sum(arm.label == "always_deep" for arm in plan) == 18
    assert {arm.label for arm in plan} == {"auto", "always_deep"}
    assert all(arm.model == "gpt-6-astra" for arm in plan if arm.label == "always_deep")
    assert next(arm for arm in plan if arm.case_id == "plus-summary-001" and arm.label == "auto").route_tier == "fast"
    assert next(arm for arm in plan if arm.case_id == "plus-debugging-001" and arm.label == "auto").route_tier == "deep"


def test_dry_run_does_not_resolve_or_call_codex(tmp_path: Path):
    result = run_plus_eval(
        cases_path=None, output=tmp_path / "results.jsonl", workspace=tmp_path / "workspace",
        codex_path="definitely-missing", execute=False,
    )
    assert result["mode"] == "dry-run"
    assert result["resume_status"].startswith("conservative preview")
    assert result["pending_calls"] == 36
    assert all(set(route) == {"key", "category", "model", "effort", "tier"} for route in result["routes"])


def test_call_cap_above_twelve_requires_explicit_override(tmp_path: Path):
    with pytest.raises(ValueError, match="allow-more-calls"):
        run_plus_eval(
            cases_path=None, output=tmp_path / "results.jsonl", workspace=tmp_path,
            codex_path=None, execute=False, max_calls=13,
        )


def test_chatgpt_login_is_required():
    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="Logged in using ChatGPT\n", stderr="")

    status = codex_login_status("codex", runner=fake_runner)
    assert status["available"] is True
    assert status["chatgpt_login"] is True


def test_find_codex_skips_candidates_that_cannot_start(monkeypatch):
    candidates = ["broken-codex.cmd", "healthy-codex.exe"]
    monkeypatch.setattr("layman_router.plus_eval._codex_candidates", lambda: candidates)
    attempted = []

    def fake_runner(command, **kwargs):
        attempted.append(command[0])
        return subprocess.CompletedProcess(command, 0 if command[0] == candidates[1] else 1, stdout="", stderr="")

    assert find_codex(runner=fake_runner) == candidates[1]
    assert attempted == candidates


def test_find_codex_reports_when_all_candidates_are_broken(monkeypatch):
    monkeypatch.setattr("layman_router.plus_eval._codex_candidates", lambda: ["broken-codex.cmd"])

    def fake_runner(command, **kwargs):
        raise OSError("not executable")

    with pytest.raises(FileNotFoundError, match="none could start"):
        find_codex(runner=fake_runner)


def test_run_arm_passes_prompt_on_stdin_and_redacts_text(tmp_path: Path):
    captured = {}

    def fake_runner(command, **kwargs):
        captured["command"] = command
        captured["input"] = kwargs["input"]
        captured["env"] = kwargs["env"]
        message_path = Path(command[command.index("--output-last-message") + 1])
        message_path.write_text("secret model answer", encoding="utf-8")
        stdout = json.dumps({"type": "turn.completed", "usage": {"input_tokens": 11, "cached_input_tokens": 2, "output_tokens": 7}})
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    arm = PlusEvalArm("case-1", "summary", "auto", "model-a", "low", "fast", ["test"], "secret prompt")
    record = run_arm(arm, codex_path="codex", workspace=tmp_path, runner=fake_runner)
    assert captured["input"].endswith("secret prompt")
    assert "secret prompt" not in " ".join(captured["command"])
    assert "OPENAI_API_KEY" not in captured["env"]
    assert "CODEX_API_KEY" not in captured["env"]
    assert "answer_text" not in record
    assert record["usage"]["input_tokens"] == 11
    assert record["answer_chars"] == len("secret model answer")


def test_run_arm_removes_api_billing_environment(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-reach-codex")
    monkeypatch.setenv("CODEX_API_KEY", "must-not-reach-codex")
    captured = {}

    def fake_runner(command, **kwargs):
        captured.update(kwargs["env"])
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="usage limit reached")

    arm = PlusEvalArm("case-1", "summary", "auto", "model-a", "low", "fast", ["test"], "prompt")
    run_arm(arm, codex_path="codex", workspace=tmp_path, runner=fake_runner)
    assert "OPENAI_API_KEY" not in captured
    assert "CODEX_API_KEY" not in captured


def test_resume_only_accepts_completed_records(tmp_path: Path):
    output = tmp_path / "results.jsonl"
    output.write_text(
        json.dumps({"key": "a:auto", "status": "completed", "experiment_fingerprint": "current"}) + "\n" +
        json.dumps({"key": "b:auto", "status": "completed", "experiment_fingerprint": "old"}) + "\n" +
        json.dumps({"key": "c:auto", "status": "failed", "experiment_fingerprint": "current"}) + "\n",
        encoding="utf-8",
    )
    assert completed_keys(output, "current") == {"a:auto"}


def test_experiment_fingerprint_changes_with_cases_routes_or_codex(router_config):
    cases = load_cases()
    plan = build_plan(cases, config=router_config)
    current = experiment_fingerprint(cases, plan, codex_version="codex 1")
    assert current == experiment_fingerprint(cases, plan, codex_version="codex 1")
    assert current != experiment_fingerprint(cases, plan, codex_version="codex 2")
    changed_cases = [*cases]
    changed_cases[0] = {**changed_cases[0], "input": changed_cases[0]["input"] + " changed"}
    assert current != experiment_fingerprint(changed_cases, plan, codex_version="codex 1")


@pytest.fixture
def fake_calibration(monkeypatch, tmp_path):
    monkeypatch.setattr(plus_eval, "find_codex", lambda _: "fake")
    monkeypatch.setattr(plus_eval, "codex_login_status", lambda _: {"available": True, "chatgpt_login": True})
    monkeypatch.setattr(plus_eval.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a[0], 0, stdout="fake-version", stderr=""))
    return {"cases_path": None, "output": tmp_path / "results.jsonl", "workspace": tmp_path / "workspace",
            "codex_path": "fake", "execute": True, "max_calls": 1, "total_call_cap": 3}


def test_calibration_cap_counts_failures_across_batches(fake_calibration, monkeypatch):
    calls = []

    def arm_runner(arm, **kwargs):
        calls.append(arm.key)
        return {"key": arm.key, "status": "failed" if len(calls) == 1 else "completed",
                "experiment_fingerprint": kwargs["experiment_fingerprint_value"]}

    monkeypatch.setattr(plus_eval, "run_arm", arm_runner)
    results = [run_plus_eval(**fake_calibration) for _ in range(4)]
    assert results[0]["failed_now"] == 1
    assert results[-1]["completed_now"] == 0
    assert results[-1]["authorized_attempts_remaining"] == 0
    assert len(calls) == len(set(calls)) == 3
    journal = fake_calibration["output"].with_name("results.jsonl.attempts.jsonl")
    assert len(journal.read_text().splitlines()) == 3


def test_interrupted_calibration_is_not_replayed(fake_calibration, monkeypatch):
    def interrupted(*args, **kwargs):
        raise RuntimeError("synthetic interruption")

    monkeypatch.setattr(plus_eval, "run_arm", interrupted)
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        run_plus_eval(**fake_calibration)
    monkeypatch.setattr(plus_eval, "run_arm", lambda *a, **k: pytest.fail("No replay permitted"))
    with pytest.raises(RuntimeError, match="Interrupted reserved"):
        run_plus_eval(**fake_calibration)
    assert not fake_calibration["output"].with_name("results.jsonl.lock").exists()


def test_concurrent_calibration_is_blocked_before_codex(fake_calibration, monkeypatch):
    output = fake_calibration["output"]
    lock = output.with_name("results.jsonl.lock")
    lock.write_text("existing-owner", encoding="utf-8")
    monkeypatch.setattr(plus_eval, "find_codex", lambda _: pytest.fail("Locked runner must not reach Codex"))
    with pytest.raises(RuntimeError, match="writer lock exists"):
        run_plus_eval(**fake_calibration)
    assert lock.read_text() == "existing-owner"


@pytest.mark.parametrize("status", ["completed", "failed"])
@pytest.mark.parametrize("partial_journal", [False, True])
def test_unreserved_historical_results_refuse_capped_execution(fake_calibration, monkeypatch, status, partial_journal):
    output = fake_calibration["output"]
    rows = [{"key": "old:auto", "status": status, "experiment_fingerprint": "old-protocol"}]
    if partial_journal:
        rows.insert(0, {"key": "recorded:auto", "status": "completed", "experiment_fingerprint": "old-protocol"})
        output.with_name("results.jsonl.attempts.jsonl").write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    original = "\n".join(json.dumps(row) for row in rows) + "\n"
    output.write_text(original, encoding="utf-8")
    monkeypatch.setattr(plus_eval, "run_arm", lambda *a, **k: pytest.fail("Ambiguous budget must not launch"))
    with pytest.raises(RuntimeError, match="Unreserved historical"):
        run_plus_eval(**fake_calibration)
    assert output.read_text(encoding="utf-8") == original
    journal = output.with_name("results.jsonl.attempts.jsonl")
    assert (len(journal.read_text().splitlines()) if journal.exists() else 0) == int(partial_journal)


def test_duplicate_result_rows_are_not_hidden_by_set_matching(fake_calibration, monkeypatch):
    output = fake_calibration["output"]
    row = {"key": "old:auto", "status": "completed", "experiment_fingerprint": "old-protocol"}
    output.write_text((json.dumps(row) + "\n") * 2, encoding="utf-8")
    output.with_name("results.jsonl.attempts.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    monkeypatch.setattr(plus_eval, "run_arm", lambda *a, **k: pytest.fail("Ambiguous duplicate rows must not launch"))
    with pytest.raises(RuntimeError, match="Unreserved historical"):
        run_plus_eval(**fake_calibration)
