from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest
from layman_router.execution_control import process_launch_options
from layman_router.plus_run import plus_task_plan

from evals.token_optimization import benchmark
from evals.token_optimization.benchmark import (
    _completed_keys,
    _public_record,
    _selected_cases,
    run_benchmark,
)
from evals.token_optimization.cases import CASES
from evals.token_optimization.fixture import prepare_workspace, validate_workspace


def test_benchmark_has_exact_category_distribution():
    counts = {category: sum(case.category == category for case in CASES) for category in {case.category for case in CASES}}
    assert counts == {"bugfix": 6, "feature": 6, "refactor": 5, "testing": 5, "docs_config": 4, "high_risk": 4}


def test_benchmark_expected_tiers_match_current_lean_policy(router_config):
    routes = {
        case.id: plus_task_plan(case.prompt, config=router_config)["route_tier"]
        for case in CASES
    }
    assert all(routes[case.id] == case.expected_tier for case in CASES)
    assert {tier: list(routes.values()).count(tier) for tier in ("fast", "balanced", "deep")} == {
        "fast": 4,
        "balanced": 22,
        "deep": 4,
    }


def test_dry_run_plans_sixty_calls_without_codex(tmp_path: Path):
    args = argparse.Namespace(
        output=tmp_path / "results.jsonl", work_root=tmp_path / "work", seed=20260716,
        run=False, max_calls=20, allow_more_calls=False, codex_path="missing",
    )
    result = run_benchmark(args)
    assert result["cases"] == 30
    assert result["planned_calls"] == 60
    assert result["pending_calls"] == 60
    assert len(result["experiment_digest"]) == 64

    args.seed += 1
    changed_seed = run_benchmark(args)
    assert changed_seed["experiment_digest"] != result["experiment_digest"]


def test_pilot_selects_six_categories_before_execution():
    selected = _selected_cases(True)
    assert len(selected) == 6
    assert len({case.category for case in selected}) == 6
    assert selected[-1].read_only is True


def test_invalid_batch_cap_is_rejected_before_launch(tmp_path):
    args = argparse.Namespace(max_calls=-1)
    with pytest.raises(ValueError, match="positive integer"):
        run_benchmark(args)


def test_persistent_attempt_cap_counts_both_arms_and_survives_restart(tmp_path, monkeypatch):
    launches = []
    args = argparse.Namespace(
        output=tmp_path / "results.jsonl", work_root=tmp_path / "work", seed=20261009,
        run=True, max_calls=12, allow_more_calls=False, codex_path="fake", pilot=True, total_call_cap=2,
    )
    monkeypatch.setattr(benchmark, "find_codex", lambda _: "fake")
    monkeypatch.setattr(benchmark, "codex_login_status", lambda _: {"available": True, "chatgpt_login": True})
    monkeypatch.setattr(benchmark.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a[0], 0, stdout="test-version", stderr=""))
    monkeypatch.setattr(benchmark, "prepare_workspace", lambda case, path: path.mkdir(parents=True))
    monkeypatch.setattr(benchmark, "validate_workspace", lambda *a: {"passed": True})

    def execution(*args, **kwargs):
        launches.append(kwargs)
        return {"status": "completed", "usage": {"input_tokens": 10, "output_tokens": 2}, "answer": "synthetic"}

    monkeypatch.setattr(benchmark, "_direct_run", execution)
    monkeypatch.setattr(benchmark, "run_plus_task", execution)
    first = run_benchmark(args)
    second = run_benchmark(args)
    assert first["reserved_attempts_total"] == 2
    assert first["authorized_attempts_remaining"] == second["authorized_attempts_remaining"] == 0
    assert first["remaining"] > first["authorized_attempts_remaining"]
    assert second["completed_now"] == 0
    assert len(launches) == 2
    assert any(call.get("max_model_attempts") == 1 for call in launches)


def test_analysis_excludes_incomplete_usage_not_as_free_savings(tmp_path):
    output = tmp_path / "results.jsonl"
    rows = [
        {"case_id": "bugfix-01", "arm": arm, "experiment_digest": "d", "execution_status": "completed",
         "validation": {"passed": True}, "usage": {"input_tokens": count, "output_tokens": 1},
         "total_tokens": count + 1, "usage_incomplete": arm == "layman"}
        for arm, count in [("direct", 100), ("layman", 0)]
    ]
    output.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    result = benchmark.analyze(output)
    assert result["pairs"] == 1
    assert result["usage_eligible_pairs"] == 0
    assert result["median_total_token_reduction"] is None
    assert result["claim_token_savings"] is False
    assert result["gates"]["trusted_usage_protocol"] is False


def test_direct_baseline_is_balanced_medium_not_deep(tmp_path, monkeypatch, router_config):
    seen = []
    monkeypatch.setattr(benchmark, "load_config", lambda: router_config)

    def runner(command, **kwargs):
        for key, value in process_launch_options().items():
            assert kwargs[key] == value
        seen.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(benchmark.subprocess, "run", runner)
    result = benchmark._direct_run(CASES[0], tmp_path, "fake")
    assert result["model"] == "gpt-6.1-sol"
    assert result["effort"] == "medium"
    assert seen[0][seen[0].index("-m") + 1] == "gpt-6.1-sol"
    assert result["usage_incomplete"] is True


def test_direct_error_classifies_structured_events_without_retaining_text():
    diagnostic = json.dumps({"type": "turn.failed", "error": {"message": "usage limit reached private-data"}})
    assert benchmark._execution_error(diagnostic, "", 1) == "subscription_limit"
    assert benchmark._execution_error("", "Error loading config: private-path", 1) == "cli_configuration"
    assert benchmark._execution_error("", "unexpected argument private-value", 2) == "cli_arguments"
    assert benchmark._execution_error('{"type":"item.completed","message":"quota"}', "", 1) == "codex_exit_1"


def test_usage_implementation_change_invalidates_benchmark_fingerprint(monkeypatch):
    original = Path.read_bytes
    before = benchmark._experiment_manifest(20261009)

    def changed_read(path):
        value = original(path)
        return value + b"\n# synthetic change" if path.name == "execution_control.py" else value

    monkeypatch.setattr(Path, "read_bytes", changed_read)
    after = benchmark._experiment_manifest(20261009)
    assert before["usage_protocol_sha256"] != after["usage_protocol_sha256"]
    assert before["experiment_digest"] != after["experiment_digest"]


def test_startup_diagnostics_keep_only_known_top_level_counters():
    stdout = "\n".join([
        "private non-json log",
        json.dumps({"type": "thread.started", "thread_id": "private-thread"}),
        json.dumps({"type": "turn.started"}),
        json.dumps({"type": "item.completed", "result": {"type": "turn.completed", "text": "private-answer"}}),
        json.dumps({"type": "turn.failed", "error": {"message": "private-error"}}),
        json.dumps({"type": ["unexpected"]}),
    ])
    diagnostic = benchmark._startup_diagnostics(stdout, "private stderr", 1)
    assert diagnostic == {
        "exit_code": 1,
        "stderr_present": True,
        "lifecycle_counts": {"thread.started": 1, "turn.started": 1, "turn.completed": 0, "turn.failed": 1, "error": 0},
    }
    assert "private" not in json.dumps(diagnostic)


def test_direct_failure_publishes_stage_and_missing_usage_not_raw_diagnostics(tmp_path, monkeypatch, router_config):
    monkeypatch.setattr(benchmark, "load_config", lambda: router_config)
    monkeypatch.setattr(benchmark.subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(
        command, 1, stdout="", stderr="Error loading config: private-file-path",
    ))
    result = benchmark._direct_run(CASES[0], tmp_path, "fake")
    assert result["error_category"] == "cli_configuration"
    assert result["usage_incomplete"] is True
    assert result["startup_diagnostics"]["exit_code"] == 1
    assert not any(result["startup_diagnostics"]["lifecycle_counts"].values())
    record = _public_record(CASES[0], "direct", result, {"passed": False})
    assert "private-file-path" not in json.dumps(record)


def test_relative_workspace_is_resolved_before_setting_subprocess_cwd(tmp_path, monkeypatch, router_config):
    monkeypatch.chdir(tmp_path)
    workspace = Path("work") / "fixture"
    workspace.mkdir(parents=True)
    expected = workspace.resolve()
    monkeypatch.setattr(benchmark, "load_config", lambda: router_config)

    def runner(command, **kwargs):
        assert kwargs["cwd"] == expected
        assert Path(command[command.index("-C") + 1]) == expected
        assert expected.is_dir()
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({
            "type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 10},
        }), stderr="")

    monkeypatch.setattr(benchmark.subprocess, "run", runner)
    result = benchmark._direct_run(CASES[0], workspace, "fake")
    assert result["status"] == "completed"
    assert result["usage_incomplete"] is False


def test_checkpoint_does_not_reuse_a_result_from_another_policy(tmp_path: Path):
    output = tmp_path / "results.jsonl"
    output.write_text(
        '{"key":"bugfix-01:layman","execution_status":"completed",'
        '"experiment_digest":"old-policy"}\n',
        encoding="utf-8",
    )
    assert _completed_keys(output, "current-policy") == set()
    assert _completed_keys(output, "old-policy") == {"bugfix-01:layman"}


def test_read_only_fixture_requires_no_changes_and_required_plan_terms(tmp_path: Path):
    case = next(case for case in CASES if case.id == "risk-01")
    prepare_workspace(case, tmp_path / "fixture")
    result = validate_workspace(case, tmp_path / "fixture", "备份后验证，失败时回滚，并设置停止条件。")
    assert result["passed"] is True


def test_testing_fixture_reports_untracked_test_file_not_parent_directory(tmp_path: Path):
    case = next(case for case in CASES if case.id == "testing-01")
    workspace = tmp_path / "fixture"
    prepare_workspace(case, workspace)
    test_path = workspace / "tests" / "test_target.py"
    test_path.parent.mkdir()
    test_path.write_text(
        "from src.target import is_even\n\n"
        "def test_values():\n"
        "    assert is_even(2)\n"
        "    assert is_even(-2)\n"
        "    assert not is_even(3)\n"
        "    assert is_even(0)\n",
        encoding="utf-8",
    )
    result = validate_workspace(case, workspace, "")
    assert result["passed"] is True
    assert result["changed_files"] == ["tests/test_target.py"]


def test_public_record_never_contains_answer_text():
    case = CASES[0]
    record = _public_record(
        case,
        "layman",
        {"status": "completed", "usage": {"input_tokens": 10, "output_tokens": 2}, "answer": "private answer"},
        {"passed": True, "quality_ok": True, "scope_ok": True, "changed_files": [], "validation_reason": "ok"},
    )
    assert "answer" not in record
    assert "private answer" not in str(record)
    assert record["answer_chars"] == len("private answer")
