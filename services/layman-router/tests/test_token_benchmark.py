from __future__ import annotations

import argparse
from pathlib import Path

from evals.token_optimization.benchmark import _completed_keys, _public_record, run_benchmark
from evals.token_optimization.cases import CASES
from evals.token_optimization.fixture import prepare_workspace, validate_workspace
from layman_router.plus_run import plus_task_plan


def test_benchmark_has_exact_category_distribution():
    counts = {category: sum(case.category == category for case in CASES) for category in {case.category for case in CASES}}
    assert counts == {"bugfix": 6, "feature": 6, "refactor": 5, "testing": 5, "docs_config": 4, "high_risk": 4}


def test_benchmark_expected_tiers_match_current_lean_policy(router_config):
    routes = {
        case.id: plus_task_plan(case.prompt, config=router_config)["route_tier"]
        for case in CASES
    }
    assert all(routes[case.id] == case.expected_tier for case in CASES)
    assert {tier: list(routes.values()).count(tier) for tier in {"fast", "balanced", "deep"}} == {
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
