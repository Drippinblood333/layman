from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("adaptive_reasoning_v1_benchmark", HERE / "benchmark.py")
assert SPEC and SPEC.loader
benchmark = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = benchmark
SPEC.loader.exec_module(benchmark)


def test_validate_only_accepts_30_independent_cases():
    result = benchmark.validate_only()
    assert result["passed"] is True
    assert result["cases"] == 30
    assert result["fixtures"] == 30
    assert result["category_counts"] == {
        "mechanical": 5,
        "single_file_coding": 6,
        "multi_file_tool_use": 6,
        "debugging": 5,
        "architecture_semantic": 4,
        "high_risk_read_only": 4,
    }


def test_dry_run_plans_180_calls_without_writing_results(tmp_path: Path):
    results = tmp_path / "results.jsonl"
    args = argparse.Namespace(
        include_optional=False,
        seed=20260815,
        results=results,
        max_calls=6,
        max_estimated_usd=200.0,
        case_id=[],
        max_retries=None,
    )
    result = benchmark.dry_run(args)
    assert result["paid_calls_started"] is False
    assert result["planned_execution_calls"] == 180
    assert result["pending_execution_arms"] == 180
    assert len(result["next"]) == 6
    assert not results.exists()


def test_fingerprint_includes_randomization_seed():
    cases, arms, protocol = benchmark.load_cases(), benchmark.load_arms(), benchmark.load_protocol()
    first, _ = benchmark.experiment_fingerprint(cases, arms, protocol, 1)
    second, _ = benchmark.experiment_fingerprint(cases, arms, protocol, 2)
    assert first != second


def test_stage_a_subset_plans_exactly_36_execution_and_18_judge_calls(tmp_path: Path):
    args = argparse.Namespace(
        include_optional=False,
        seed=20260815,
        results=tmp_path / "results.jsonl",
        max_calls=65,
        max_estimated_usd=35.0,
        max_retries=0,
        case_id=[
            "mech-inventory-reconcile", "single-ttl-boundary", "multi-config-precedence",
            "debug-retry-budget", "arch-idempotent-ingestion", "risk-secret-rotation",
        ],
    )
    result = benchmark.dry_run(args)
    assert result["cases"] == 6
    assert result["planned_execution_calls"] == 36
    assert result["budget_ceiling"]["semantic_review_calls"] == 18
    assert result["budget_ceiling"]["max_attempts_with_configured_retries"] == 54
    assert result["budget_ceiling"]["combined_cost_ceiling_usd"] <= 35.0


def test_single_arm_selection_is_exact_and_does_not_change_arm_definition(tmp_path: Path):
    args = argparse.Namespace(
        include_optional=False, seed=20260815, results=tmp_path / "results.jsonl",
        max_calls=1, max_estimated_usd=2.0, max_retries=0,
        case_id=["mech-inventory-reconcile"], arm_id=["sol-medium"],
    )
    cases, arms, protocol = benchmark.selected_experiment(args)
    assert [case["case_id"] for case in cases] == ["mech-inventory-reconcile"]
    assert arms == [{"arm_id": "sol-medium", "model": "gpt-6.1-sol", "reasoning_effort": "medium", "compute_rank": 3}]
    assert protocol["max_retries"] == 0


def test_windows_shell_launchers_are_not_directly_spawnable(tmp_path: Path):
    shim = tmp_path / "codex.cmd"
    shim.write_text("@echo off\r\n", encoding="utf-8")
    candidate = benchmark.CodexCliBackend().resolve(str(shim))[0]
    assert candidate.kind == "windows-command-shim"
    assert candidate.directly_spawnable is False


def test_execution_diagnostic_redacts_credentials_and_is_bounded():
    diagnostic = benchmark.CodexCliBackend._execution_diagnostic(
        "request failed Bearer abc.secret token-verysecret " + "x" * 1000
    )
    assert diagnostic is not None
    assert "abc.secret" not in diagnostic
    assert "verysecret" not in diagnostic
    assert len(diagnostic) <= 500


def test_direct_spawn_preserves_space_chinese_and_special_character_cwd(tmp_path: Path):
    cwd = tmp_path / "有 空格 & (stage-a0)"
    cwd.mkdir()
    completed = benchmark.CodexCliBackend._capture(
        [sys.executable, "-c", "import os,sys;print(os.getcwd());sys.stderr.write('captured')"],
        cwd=cwd, timeout=10, env=os.environ.copy(),
    )
    assert completed.returncode == 0
    assert Path(completed.stdout.strip()).resolve() == cwd.resolve()
    assert completed.stderr == "captured"


def test_terra_medium_exact_command_contract_is_explicit_and_prompt_private(tmp_path: Path):
    workspace = tmp_path / "有 空格 & (fixture)"
    output_parent = tmp_path / "输出 & result"
    workspace.mkdir()
    output_parent.mkdir()
    launcher = benchmark.LauncherCandidate(
        path=sys.executable, kind="native-exe", source="test", directly_spawnable=True,
    )
    prompt = "SECRET PROMPT 正文 & do not persist"
    request = benchmark.CodexExecutionRequest(
        workspace=workspace,
        prompt=prompt,
        model="gpt-6.1-sol",
        reasoning_effort="medium",
        max_output_tokens=4096,
        timeout_seconds=60,
        read_only=False,
        output_path=output_parent / "last message.txt",
    )
    contract = benchmark.CodexCliBackend().build_command_contract(request, launcher)
    args = list(contract.args)
    assert args[:3] == ["--ask-for-approval", "never", "exec"]
    assert args[-1] == "-"
    assert args[args.index("-m") + 1] == "gpt-6.1-sol"
    assert 'model_reasoning_effort="medium"' in args
    assert args[args.index("--sandbox") + 1] == "workspace-write"
    assert args[args.index("-C") + 1] == str(workspace.resolve())
    assert args[args.index("--output-last-message") + 1] == str(request.output_path.resolve())
    assert {"--json", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check"} <= set(args)
    assert contract.prompt_transport == "stdin"
    assert contract.stdin_policy == "pipe_prompt_then_close"
    assert contract.shell is False
    assert prompt not in json.dumps(contract.public_dict(), ensure_ascii=False)


def test_exec_contract_preflight_parses_exact_command_without_model_call(tmp_path: Path, monkeypatch):
    controlled_root = tmp_path / "controlled work"
    workspace = controlled_root / "fixture 中文 & special"
    output_parent = controlled_root / "diagnostics"
    workspace.mkdir(parents=True)
    output_parent.mkdir()
    launcher = benchmark.LauncherCandidate(
        path=sys.executable, kind="native-exe", source="test", directly_spawnable=True,
    )
    request = benchmark.CodexExecutionRequest(
        workspace=workspace,
        prompt="PRIVATE PROMPT",
        model="gpt-6.1-sol",
        reasoning_effort="medium",
        max_output_tokens=4096,
        timeout_seconds=60,
        read_only=False,
        output_path=output_parent / "last-message.txt",
    )
    calls: list[list[str]] = []
    required_flags = (
        "--json --ephemeral --ignore-user-config --ignore-rules "
        "--skip-git-repo-check --sandbox --output-last-message"
    )

    def fake_capture(command, *, cwd, timeout, env):
        command = list(command)
        calls.append(command)
        if command[:3] == ["git", "rev-parse", "--is-inside-work-tree"]:
            return subprocess.CompletedProcess(command, 0, "true\n", "")
        if command[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(command, 0, str(controlled_root) + "\n", "")
        if command[-1] == "--version":
            return subprocess.CompletedProcess(command, 0, "codex-cli test-version\n", "")
        assert command[-1] == "--help"
        assert "exec" in command
        assert "-" not in command[command.index("exec") + 1:]
        return subprocess.CompletedProcess(command, 0, required_flags, "")

    backend = benchmark.CodexCliBackend()
    monkeypatch.setattr(backend, "_capture", fake_capture)
    result = backend.preflight_exec_contract(
        request, launcher, controlled_work_root=controlled_root,
    )
    assert result.passed is True
    assert result.model_calls_started == 0
    assert result.exact_command_parse_ok is True
    assert result.user_config_isolated is True
    assert result.auth_uses_codex_home is True
    assert result.output_parent_exists is True
    assert result.executable_identity["codex_cli_version"] == "codex-cli test-version"
    assert all(result.cli_flag_support.values())
    assert all(command[0] == "git" or command[-1] in {"--help", "--version"} for command in calls)
    assert "PRIVATE PROMPT" not in json.dumps(result.public_dict(), ensure_ascii=False)


def test_exec_contract_rejects_skip_git_for_arbitrary_workspace(tmp_path: Path, monkeypatch):
    controlled_root = tmp_path / "controlled"
    controlled_root.mkdir()
    workspace = tmp_path / "outside"
    workspace.mkdir()
    output = tmp_path / "out" / "last.txt"
    output.parent.mkdir()
    launcher = benchmark.LauncherCandidate(
        path=sys.executable, kind="native-exe", source="test", directly_spawnable=True,
    )
    request = benchmark.CodexExecutionRequest(
        workspace=workspace, prompt="PRIVATE", model="gpt-6.1-sol",
        reasoning_effort="medium", max_output_tokens=4096, timeout_seconds=60,
        read_only=False, output_path=output,
    )

    def fake_capture(command, *, cwd, timeout, env):
        command = list(command)
        if command[0] == "git":
            return subprocess.CompletedProcess(command, 128, "", "not a repository")
        return subprocess.CompletedProcess(
            command, 0,
            "--json --ephemeral --ignore-user-config --ignore-rules "
            "--skip-git-repo-check --sandbox --output-last-message",
            "",
        )

    backend = benchmark.CodexCliBackend()
    monkeypatch.setattr(backend, "_capture", fake_capture)
    result = backend.preflight_exec_contract(
        request, launcher, controlled_work_root=controlled_root,
    )
    assert result.passed is False
    assert result.controlled_workspace is False
    assert any(
        "workspace_not_under_controlled_root" in item.get("errors", [])
        for item in result.diagnostics
    )


def test_execute_is_blocked_without_exact_contract_preflight(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output = tmp_path / "output" / "last.txt"
    output.parent.mkdir()
    launcher = benchmark.LauncherCandidate(
        path=sys.executable, kind="native-exe", source="test", directly_spawnable=True,
    )
    request = benchmark.CodexExecutionRequest(
        workspace=workspace, prompt="PRIVATE", model="gpt-6.1-sol",
        reasoning_effort="medium", max_output_tokens=4096, timeout_seconds=60,
        read_only=False, output_path=output,
    )
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: pytest.fail("must not spawn"))
    with pytest.raises(RuntimeError, match="exec-contract preflight"):
        benchmark.CodexCliBackend().execute(request, launcher)


def test_experiment_fingerprint_names_stable_execution_contract_semantics():
    cases, arms, protocol = benchmark.load_cases(), benchmark.load_arms(), benchmark.load_protocol()
    _fingerprint, components = benchmark.experiment_fingerprint(cases, arms, protocol, 20260815)
    assert components["execution_contract"]["stdin_policy"] == "pipe_prompt_then_close"
    assert components["execution_contract"]["user_config"] == "--ignore-user-config"
    assert components["execution_contract"]["git_repo_check"].startswith("--skip-git-repo-check only")
    assert components["execution_contract_sha256"] == benchmark.CodexCliBackend.contract_semantics_sha256()


def test_runtime_execution_fingerprint_includes_executable_identity():
    base = "f" * 64
    first = benchmark.runtime_execution_metadata({
        "codex_cli_version": "codex-cli 1",
        "codex_executable_sha256": "a" * 64,
        "codex_distribution_source": "vscode-extension-native",
        "vscode_extension_version": "1.2.3",
    }, "c" * 64)
    second = {**first, "codex_executable_sha256": "b" * 64}
    assert benchmark.runtime_execution_fingerprint(base, first) != benchmark.runtime_execution_fingerprint(base, second)


def test_spawn_is_blocked_if_executable_identity_changes_after_preflight(tmp_path: Path, monkeypatch):
    controlled_root = tmp_path / "controlled"
    workspace = controlled_root / "fixture"
    output = controlled_root / "output" / "last.txt"
    workspace.mkdir(parents=True)
    output.parent.mkdir()
    launcher = benchmark.LauncherCandidate(
        path=sys.executable, kind="native-exe", source="test", directly_spawnable=True,
    )
    request = benchmark.CodexExecutionRequest(
        workspace=workspace, prompt="PRIVATE", model="gpt-6.1-sol",
        reasoning_effort="medium", max_output_tokens=4096, timeout_seconds=60,
        read_only=False, output_path=output,
    )
    backend = benchmark.CodexCliBackend()
    backend._approved_launcher_path = os.path.normcase(str(Path(sys.executable).resolve()))
    backend._controlled_work_root = controlled_root.resolve()
    backend._approved_model_efforts.add((request.model, request.reasoning_effort))
    backend._approved_identity = benchmark.ExecutableIdentity(
        "codex-cli approved", "a" * 64, "native-executable", None,
    )
    monkeypatch.setattr(
        backend,
        "_executable_identity",
        lambda *args, **kwargs: benchmark.ExecutableIdentity(
            "codex-cli changed", "b" * 64, "native-executable", None,
        ),
    )
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: pytest.fail("must not spawn"))
    with pytest.raises(RuntimeError, match="hash/version changed"):
        backend.execute(request, launcher)


@pytest.mark.parametrize(
    ("stderr", "expected"),
    [
        ("authentication required", "authentication"),
        ("unsupported model gpt-x", "model unavailable"),
        ("invalid model_reasoning_effort", "reasoning effort/config invalid"),
        ("failed to initialize sandbox", "sandbox/workspace initialization"),
        ("connection reset", "network"),
        ("subscription entitlement missing", "account/subscription"),
        ("unexpected argument --bad", "CLI contract"),
        ("internal startup failure", "unknown"),
    ],
)
def test_failure_category_is_specific_without_guessing(stderr: str, expected: str):
    assert benchmark.CodexCliBackend.classify_failure_category(
        returncode=1, stop_reason=None, stderr=stderr,
    ) == expected


def test_pricing_snapshot_matches_core_arm_capabilities():
    pricing = benchmark.load_pricing_snapshot()
    assert pricing["price_version"] == "openai-standard-2026-10-09"
    for arm in benchmark.load_arms():
        assert arm["reasoning_effort"] in pricing["models"][arm["model"]]["supported_reasoning_efforts"]


@pytest.mark.parametrize(
    ("stop_reason", "returncode", "stderr", "expected"),
    [
        ("timeout", 1, "", "infrastructure_timeout"),
        (None, 1, "HTTP 429 rate limit", "infrastructure_rate_limit"),
        (None, 1, "connection reset by peer", "infrastructure_network"),
        (None, 1, "Error: spawn EFTYPE", "infrastructure_launcher"),
        (None, 2, "invalid option", None),
    ],
)
def test_infrastructure_error_is_bounded_and_privacy_safe(stop_reason, returncode, stderr, expected):
    assert benchmark.infrastructure_error(stop_reason, returncode, stderr) == expected


def test_lowest_sufficient_uses_cost_then_close_cost_latency():
    protocol = benchmark.load_protocol()
    rows = [
        {"arm_id": "slow-cheapest", "sufficient": True, "estimated_cost_usd": 1.0, "latency_ms": 500, "compute_rank": 0},
        {"arm_id": "fast-close", "sufficient": True, "estimated_cost_usd": 1.01, "latency_ms": 100, "compute_rank": 1},
        {"arm_id": "too-expensive", "sufficient": True, "estimated_cost_usd": 1.10, "latency_ms": 1, "compute_rank": 2},
    ]
    assert benchmark.choose_lowest_sufficient(rows, protocol)["arm_id"] == "fast-close"


def test_sufficiency_requires_every_gate_and_best_arm_gap():
    protocol = benchmark.load_protocol()
    row = {
        "execution_success": True,
        "validator_success": True,
        "safety_passed": True,
        "evidence_complete": True,
        "semantic_quality": 4.25,
        "human_review_required": False,
        "human_review_complete": False,
    }
    assert benchmark.is_sufficient(row, 4.5, protocol) is True
    assert benchmark.is_sufficient({**row, "semantic_quality": 4.24}, 4.5, protocol) is False
    for gate in ("execution_success", "validator_success", "safety_passed", "evidence_complete"):
        assert benchmark.is_sufficient({**row, gate: False}, 4.5, protocol) is False
    assert benchmark.is_sufficient({**row, "human_review_required": True}, 4.5, protocol) is False
    assert benchmark.is_sufficient(
        {**row, "human_review_required": True, "human_review_complete": True}, 4.5, protocol
    ) is True


def test_public_result_does_not_persist_answer_prompt_or_tool_arguments():
    case = benchmark.load_cases()[0]
    arm = benchmark.load_arms()[0]
    secret = "PRIVATE_ANSWER_AND_TOOL_ARGUMENT"
    attempts = [{
        "execution_success": True,
        "execution_error": None,
        "usage": {"input_tokens": 10, "reasoning_tokens": 1, "output_tokens": 3, "cached_tokens": 0, "cache_write_tokens": 0},
        "latency_ms": 20,
        "tool_calls": 1,
        "unique_files_read": 1,
        "answer": secret,
    }]
    validation = {
        "validator_success": True,
        "safety_passed": True,
        "evidence_complete": True,
        "files_modified": 1,
        "validation_reason": "passed",
        "missing_evidence": [],
        "changed_files": ["result.json"],
    }
    record = benchmark.public_result(
        case=case,
        arm=arm,
        fingerprint="f" * 64,
        attempts=attempts,
        validation=validation,
        router_arm="luna-low",
        router_compute_ms=0.1,
        router_preflight_ms=0.2,
    )
    serialized = json.dumps(record, ensure_ascii=False)
    assert secret not in serialized
    assert case["task"] not in serialized
    assert record["stores_answer"] is False
    assert record["fallback_count"] == 0


def test_execution_failure_does_not_report_outcome_validator_as_passed():
    case = next(item for item in benchmark.load_cases() if item["case_id"] == "risk-secret-rotation")
    arm = next(item for item in benchmark.load_arms() if item["arm_id"] == "sol-medium")
    attempts = [{
        "execution_success": False, "execution_error": "infrastructure_launcher",
        "usage": {"input_tokens": 0, "reasoning_tokens": 0, "output_tokens": 0, "cached_tokens": 0, "cache_write_tokens": 0},
        "latency_ms": 10, "tool_calls": 0, "unique_files_read": 0, "answer": "",
    }]
    validation = {
        "validator_success": True, "safety_passed": True, "evidence_complete": False,
        "files_modified": 0, "validation_reason": "semantic_evidence_only", "missing_evidence": ["evidence"],
    }
    record = benchmark.public_result(
        case=case, arm=arm, fingerprint="f" * 64, attempts=attempts, validation=validation,
        router_arm="sol-high", router_compute_ms=0.1, router_preflight_ms=0.2,
    )
    assert record["precheck_success"] is True
    assert record["outcome_validation_success"] is None
    assert record["semantic_review_state"] == "not_started_no_candidate"
    assert record["task_success"] is False


def test_execute_is_hard_gated_before_executor_discovery(tmp_path: Path):
    args = argparse.Namespace(
        approve_model_calls=False,
        max_calls=1,
        max_estimated_usd=1.0,
        include_optional=False,
        seed=20260815,
        results=tmp_path / "results.jsonl",
        codex_path=None,
        work_root=tmp_path / "work",
        store_outputs=False,
        case_id=[],
        max_retries=None,
    )
    with pytest.raises(ValueError, match="approve-model-calls"):
        benchmark.execute(args)


def test_judge_is_hard_gated_before_executor_discovery(tmp_path: Path):
    args = argparse.Namespace(
        approve_model_calls=False,
        max_calls=1,
        max_estimated_usd=1.0,
        include_optional=False,
        seed=20260815,
        results=tmp_path / "results.jsonl",
        reviews=tmp_path / "reviews.jsonl",
        codex_path=None,
        case_id=[],
        max_retries=None,
    )
    with pytest.raises(ValueError, match="approve-model-calls"):
        benchmark.judge(args)


def test_high_risk_case_envelopes_are_all_read_only():
    high_risk = [case for case in benchmark.load_cases() if case["risk_class"] == "high"]
    assert len(high_risk) == 4
    assert all(case["high_risk_safety_envelope"] == {
        "mode": "read-only", "mutation_allowed": False, "network_allowed": False
    } for case in high_risk)


def test_blind_label_hides_arm_identity():
    label = benchmark.blind_label("f" * 64, "debug-retry-budget", "sol-high")
    assert label.startswith("candidate-")
    assert "sol" not in label and "high" not in label


def test_human_review_sample_is_randomized_and_at_least_twenty_percent():
    cases, arms = benchmark.load_cases(), benchmark.load_arms()
    semantic_count = sum(case["validator"].get("requires_semantic_review", False) for case in cases) * len(arms)
    sample = benchmark.human_review_sample_keys(cases, arms, 0.2, 20260815)
    assert len(sample) == 16
    assert len(sample) / semantic_count >= 0.2


def test_mechanical_validator_accepts_exact_hidden_result(tmp_path: Path):
    case = next(item for item in benchmark.load_cases() if item["case_id"] == "mech-incident-timeline")
    workspace = tmp_path / "workspace"
    benchmark.materialize_fixture(case, workspace)
    before = benchmark.snapshot_workspace(workspace)
    (workspace / "result.json").write_text(
        json.dumps(benchmark.MECHANICAL_EXPECTED[case["case_id"]]), encoding="utf-8"
    )
    validation = benchmark.validate_case(case, workspace, "", before)
    assert validation["validator_success"] is True
    assert validation["safety_passed"] is True
    assert validation["evidence_complete"] is True


def test_high_risk_validator_requires_read_only_workspace_and_evidence(tmp_path: Path):
    case = next(item for item in benchmark.load_cases() if item["case_id"] == "risk-secret-rotation")
    workspace = tmp_path / "workspace"
    benchmark.materialize_fixture(case, workspace)
    before = benchmark.snapshot_workspace(workspace)
    answer = "Use a dual 双密钥 window, define rollback 回滚, monitoring 监控, and an approval 批准 gate."
    validation = benchmark.validate_case(case, workspace, answer, before)
    assert validation["validator_success"] is True
    assert validation["evidence_complete"] is True
    assert validation["safety_passed"] is True
    (workspace / "forbidden.txt").write_text("mutation", encoding="utf-8")
    assert benchmark.validate_case(case, workspace, answer, before)["safety_passed"] is False


def test_append_only_resume_ignores_reservation_and_partial_tail(tmp_path: Path):
    path = tmp_path / "results.jsonl"
    fingerprint = "f" * 64
    benchmark.append_event(path, {
        "event_type": "reservation", "key": "case:arm", "experiment_fingerprint": fingerprint
    })
    benchmark.append_event(path, {
        "event_type": "result", "key": "case:arm", "experiment_fingerprint": fingerprint
    })
    with path.open("a", encoding="utf-8") as stream:
        stream.write('{"event_type":"result"')
    events = benchmark.load_events(path, fingerprint)
    assert benchmark.completed_keys(events) == {"case:arm"}
