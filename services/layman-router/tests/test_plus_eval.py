from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from layman_router.plus_eval import (
    PlusEvalArm,
    build_plan,
    codex_login_status,
    completed_keys,
    experiment_fingerprint,
    find_codex,
    load_cases,
    run_arm,
    run_plus_eval,
)


def test_release_plan_is_eighteen_cases_and_thirty_six_calls(router_config):
    plan = build_plan(load_cases(), config=router_config)
    assert len(load_cases()) == 18
    assert len(plan) == 36
    assert sum(arm.label == "always_deep" for arm in plan) == 18
    assert {arm.label for arm in plan} == {"auto", "always_deep"}
    assert all(arm.model == "gpt-5.6-sol" for arm in plan if arm.label == "always_deep")
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
