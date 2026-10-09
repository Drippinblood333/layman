from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest
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


def test_direct_baseline_is_balanced_medium_not_deep(tmp_path, monkeypatch, router_config):
    seen = []
    monkeypatch.setattr(benchmark, "load_config", lambda: router_config)

    def runner(command, **kwargs):
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
