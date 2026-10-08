#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import statistics
import sys
import tempfile
import time
import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SERVICE_SRC = ROOT / "services" / "layman-router" / "src"
for path in (HERE, ROOT, SERVICE_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# ruff: disable[E402] Local benchmark imports require the path bootstrap above.
from execution_backend import (
    CodexCliBackend,
    CodexExecutionRequest,
    ExecutableIdentity,  # noqa: F401 - retained as the benchmark's public launcher-identity export.
    LauncherCandidate,
)
from fixtures import FIXTURES
from layman_router.classify import classify_task
from layman_router.config import load_config
from layman_router.execution_control import run_streaming_process
from layman_router.models import ModelPricing
from layman_router.plus_eval import (
    codex_login_status,
    find_codex,
    subscription_environment,
)
from layman_router.routing import decide_route
from layman_router.telemetry import estimate_cost
from validators import (
    HIDDEN_TESTS,
    MECHANICAL_EXPECTED,
    SEMANTIC_EVIDENCE,
    snapshot_workspace,
    validate_case,
)

# ruff: enable[E402]

DEFAULT_RESULTS = ROOT / "build" / "adaptive-reasoning-v1" / "results.jsonl"
DEFAULT_REVIEWS = ROOT / "build" / "adaptive-reasoning-v1" / "semantic-reviews.jsonl"
DEFAULT_ANALYSIS = ROOT / "build" / "adaptive-reasoning-v1" / "analysis.json"
DEFAULT_WORK_ROOT = ROOT / "build" / "adaptive-reasoning-v1" / "workspaces"
REQUIRED_RESULT_FIELDS = {
    "case_id", "arm_id", "model", "reasoning_effort", "task_success",
    "validator_success", "semantic_quality", "safety_passed", "input_tokens",
    "reasoning_tokens", "output_tokens", "cached_tokens", "cache_write_tokens",
    "latency_ms", "estimated_cost_usd", "retry_count", "fallback_count",
    "tool_calls", "unique_files_read", "files_modified", "router_compute_ms",
    "router_preflight_ms", "router_prompt_overhead_tokens", "experiment_fingerprint",
    "timestamp", "execution_error",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in (HERE / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def load_arms(*, include_optional: bool = False) -> list[dict[str, Any]]:
    data = read_json(HERE / "arms.json")
    return [*data["core"], *(data["optional"] if include_optional else [])]


def load_protocol() -> dict[str, Any]:
    return read_json(HERE / "protocol.json")


def load_pricing_snapshot() -> dict[str, Any]:
    return read_json(HERE / "pricing-snapshot.json")


def selected_experiment(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    cases = load_cases()
    requested = list(getattr(args, "case_id", None) or [])
    if requested:
        if len(requested) != len(set(requested)):
            raise ValueError("--case-id values must be unique")
        by_id = {case["case_id"]: case for case in cases}
        missing = [case_id for case_id in requested if case_id not in by_id]
        if missing:
            raise ValueError(f"unknown --case-id values: {missing}")
        cases = [by_id[case_id] for case_id in requested]
    arms = load_arms(include_optional=bool(getattr(args, "include_optional", False)))
    requested_arms = list(getattr(args, "arm_id", None) or [])
    if requested_arms:
        if len(requested_arms) != len(set(requested_arms)):
            raise ValueError("--arm-id values must be unique")
        by_arm = {arm["arm_id"]: arm for arm in arms}
        missing_arms = [arm_id for arm_id in requested_arms if arm_id not in by_arm]
        if missing_arms:
            raise ValueError(f"unknown --arm-id values: {missing_arms}")
        arms = [by_arm[arm_id] for arm_id in requested_arms]
    protocol = dict(load_protocol())
    max_retries = getattr(args, "max_retries", None)
    if max_retries is not None:
        if max_retries < 0:
            raise ValueError("--max-retries cannot be negative")
        protocol["max_retries"] = int(max_retries)
    return cases, arms, protocol


def stable_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def blind_label(fingerprint: str, case_id: str, arm_id: str) -> str:
    return "candidate-" + hashlib.sha256(f"{fingerprint}:{case_id}:{arm_id}".encode()).hexdigest()[:12]


def experiment_fingerprint(
    cases: list[dict[str, Any]],
    arms: list[dict[str, Any]],
    protocol: dict[str, Any],
    seed: int,
) -> tuple[str, dict[str, Any]]:
    pricing = load_pricing_snapshot()
    components = {
        "protocol": protocol,
        "randomization_seed": seed,
        "cases_sha256": stable_digest(cases),
        "fixtures_sha256": stable_digest(FIXTURES),
        "arms_sha256": stable_digest(arms),
        "validators_sha256": hashlib.sha256((HERE / "validators.py").read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "execution_backend_sha256": hashlib.sha256((HERE / "execution_backend.py").read_bytes()).hexdigest(),
        "execution_contract": CodexCliBackend.contract_semantics(),
        "execution_contract_sha256": CodexCliBackend.contract_semantics_sha256(),
        "price_version": pricing["price_version"],
        "pricing_sha256": stable_digest(pricing),
    }
    return stable_digest(components), components


def runtime_execution_metadata(
    executable_identity: dict[str, Any],
    execution_contract_sha256: str,
) -> dict[str, Any]:
    return {
        "codex_cli_version": executable_identity["codex_cli_version"],
        "codex_executable_sha256": executable_identity["codex_executable_sha256"],
        "codex_distribution_source": executable_identity["codex_distribution_source"],
        "vscode_extension_version": executable_identity.get("vscode_extension_version"),
        "execution_contract_sha256": execution_contract_sha256,
    }


def runtime_execution_fingerprint(
    experiment_fingerprint_value: str,
    metadata: dict[str, Any],
) -> str:
    return stable_digest({
        "experiment_fingerprint": experiment_fingerprint_value,
        "execution_runtime": metadata,
    })


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def load_events(path: Path, fingerprint: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("experiment_fingerprint") == fingerprint:
            events.append(event)
    return events


def completed_keys(events: Iterable[dict[str, Any]]) -> set[str]:
    return {str(event["key"]) for event in events if event.get("event_type") == "result"}


def materialize_fixture(case: dict[str, Any], workspace: Path) -> None:
    if workspace.exists():
        raise FileExistsError(f"Workspace already exists: {workspace}")
    workspace.mkdir(parents=True)
    for relative, content in FIXTURES[case["fixture_id"]].items():
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def remove_workspace(workspace: Path, work_root: Path) -> None:
    resolved, root = workspace.resolve(), work_root.resolve()
    resolved.relative_to(root)
    if resolved == root:
        raise RuntimeError("Refusing to delete benchmark workspace root")
    shutil.rmtree(resolved)


def case_prompt(case: dict[str, Any], protocol: dict[str, Any]) -> str:
    read_only_note = ""
    if case["high_risk_safety_envelope"]["mode"] == "read-only":
        read_only_note = (
            "\n\nREAD-ONLY OVERRIDE: If the task says to write answer.md, provide that content only in the final response. "
            "Do not create or modify any file."
        )
    history = case.get("context_history") or []
    history_text = "\n".join(f"{item['role'].upper()}: {item['content']}" for item in history)
    return (
        protocol["developer_instructions"] + "\n\n" + protocol["common_instructions"]
        + ("\n\nFIXED CONTEXT:\n" + history_text if history_text else "")
        + "\n\nTASK:\n" + case["task"] + read_only_note
    )


def ordered_plan(cases: list[dict[str, Any]], arms: list[dict[str, Any]], seed: int) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    randomizer = random.Random(seed)
    cases_ordered = list(cases)
    randomizer.shuffle(cases_ordered)
    plan: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for case in cases_ordered:
        case_arms = list(arms)
        randomizer.shuffle(case_arms)
        plan.extend((case, arm) for arm in case_arms)
    return plan


def model_pricing(model: str) -> Any:
    raw = load_pricing_snapshot()["models"].get(model)
    if raw is None:
        raise ValueError(f"No versioned price for model: {model}")
    return ModelPricing.model_validate({key: value for key, value in raw.items() if key != "supported_reasoning_efforts"})


def cost_ceiling(arm: dict[str, Any], protocol: dict[str, Any], *, judge: bool = False) -> float:
    input_tokens = int(protocol["judge_input_token_reservation_ceiling"] if judge else protocol["input_token_reservation_ceiling"])
    output_tokens = int(protocol["judge_max_output_tokens"] if judge else protocol["max_output_tokens"])
    usage = {
        "input_tokens": input_tokens,
        "cached_tokens": 0,
        "cache_write_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": output_tokens,
    }
    return estimate_cost(usage, model_pricing(arm["model"]))


def total_budget_ceiling(cases: list[dict[str, Any]], arms: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any]:
    retry_multiplier = int(protocol["max_retries"]) + 1
    execution = sum(cost_ceiling(arm, protocol) for _case in cases for arm in arms) * retry_multiplier
    semantic_cases = sum(bool(case["validator"].get("requires_semantic_review")) for case in cases)
    judge_arm = {"model": protocol["judge_model"]}
    judge_calls = semantic_cases * len(arms)
    judges = judge_calls * cost_ceiling(judge_arm, protocol, judge=True) * retry_multiplier
    return {
        "execution_calls": len(cases) * len(arms),
        "semantic_review_calls": judge_calls,
        "max_attempts_with_configured_retries": (len(cases) * len(arms) + judge_calls) * retry_multiplier,
        "execution_cost_ceiling_usd": round(execution, 6),
        "semantic_review_cost_ceiling_usd": round(judges, 6),
        "combined_cost_ceiling_usd": round(execution + judges, 6),
        "assumptions": {
            "price_version": load_pricing_snapshot()["price_version"],
            "cache": "worst-case all reserved input charged at cache-write rate",
            "execution_input_tokens_per_attempt": protocol["input_token_reservation_ceiling"],
            "execution_output_tokens_per_attempt": protocol["max_output_tokens"],
            "judge_input_tokens_per_attempt": protocol["judge_input_token_reservation_ceiling"],
            "judge_output_tokens_per_attempt": protocol["judge_max_output_tokens"],
            "retry_multiplier": retry_multiplier,
        },
    }


def current_router_arm(case: dict[str, Any], arms: list[dict[str, Any]]) -> tuple[str | None, float, float]:
    config = load_config()
    protocol = load_protocol()
    payload = {
        "model": "auto",
        "instructions": protocol["developer_instructions"] + "\n" + protocol["common_instructions"],
        "input": [
            *(case.get("context_history") or []),
            {"role": "user", "content": case["task"]},
        ],
        "tools": [
            {"type": "function", "name": tool, "description": f"Fixed benchmark {tool} tool"}
            for tool in case["tools"]
        ],
    }
    preflight_started = time.perf_counter_ns()
    compute_started = time.perf_counter_ns()
    features = classify_task(payload, config)
    decision = decide_route(features, config)
    compute_finished = time.perf_counter_ns()
    arm_id = next((arm["arm_id"] for arm in arms if arm["model"] == decision.selected_model and arm["reasoning_effort"] == decision.reasoning_effort), None)
    preflight_finished = time.perf_counter_ns()
    return arm_id, (compute_finished - compute_started) / 1_000_000, (preflight_finished - preflight_started) / 1_000_000


def normalize_usage(usage: dict[str, int]) -> dict[str, int]:
    return {
        "input_tokens": int(usage.get("input_tokens", 0)),
        "cached_tokens": int(usage.get("cached_tokens", usage.get("cached_input_tokens", 0))),
        "cache_write_tokens": int(usage.get("cache_write_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
        "reasoning_tokens": int(usage.get("reasoning_tokens", 0)),
    }


def infrastructure_error(stop_reason: str | None, returncode: int, stderr: str) -> str | None:
    if stop_reason == "timeout":
        return "infrastructure_timeout"
    lowered = stderr.lower()
    markers = {
        "spawn eftype": "infrastructure_launcher",
        "not a valid application for this os platform": "infrastructure_launcher",
        "access is denied": "infrastructure_launcher",
        "429": "infrastructure_rate_limit",
        "rate limit": "infrastructure_rate_limit",
        "timed out": "infrastructure_timeout",
        "timeout": "infrastructure_timeout",
        "connection reset": "infrastructure_network",
        "connection refused": "infrastructure_network",
        "network": "infrastructure_network",
        "dns": "infrastructure_network",
    }
    if returncode != 0:
        for marker, category in markers.items():
            if marker in lowered:
                return category
    return None


def run_attempt(
    case: dict[str, Any], arm: dict[str, Any], protocol: dict[str, Any], workspace: Path,
    backend: CodexCliBackend, launcher: LauncherCandidate,
) -> dict[str, Any]:
    read_only = case["high_risk_safety_envelope"]["mode"] == "read-only"
    with tempfile.TemporaryDirectory(prefix="adaptive-reasoning-v1-") as directory:
        answer_path = Path(directory) / "last-message.txt"
        streamed = backend.execute(
            CodexExecutionRequest(
                workspace=workspace, prompt=case_prompt(case, protocol), model=arm["model"],
                reasoning_effort=arm["reasoning_effort"], max_output_tokens=int(protocol["max_output_tokens"]),
                timeout_seconds=int(protocol["timeout_seconds"]), read_only=read_only, output_path=answer_path,
            ),
            launcher,
        )
        answer = answer_path.read_text(encoding="utf-8") if answer_path.exists() else ""
    usage = normalize_usage(streamed.usage)
    error = None if streamed.returncode == 0 and streamed.stop_reason is None else (streamed.infrastructure_error or streamed.stop_reason or f"codex_exit_{streamed.returncode}")
    return {
        "execution_success": error is None,
        "execution_error": error,
        "execution_diagnostic": streamed.diagnostic,
        "infrastructure_error": streamed.infrastructure_error is not None,
        "usage": usage,
        "usage_available": streamed.usage_available,
        "latency_ms": streamed.latency_ms,
        "tool_calls": streamed.tool_calls,
        "unique_files_read": streamed.unique_files_read,
        "effective_model": streamed.effective_model,
        "effective_reasoning_effort": streamed.effective_reasoning_effort,
        "backend_event_types": streamed.event_types,
        "backend_executable": streamed.command_executable,
        "backend_cwd": streamed.cwd,
        "backend_contract_sha256": streamed.command_contract_sha256,
        "stdout_sha256": streamed.stdout_sha256,
        "stdout_chars": streamed.stdout_chars,
        "stderr_sha256": streamed.stderr_sha256,
        "stderr_chars": streamed.stderr_chars,
        "non_json_stdout_lines": streamed.non_json_stdout_lines,
        "executable_identity": streamed.executable_identity,
        "failure_category": streamed.failure_category,
        "lifecycle": {
            "process_spawned": streamed.process_spawned,
            "codex_process_started": streamed.codex_process_started,
            "turn_started_seen": streamed.turn_started_seen,
            "turn_completed_seen": streamed.turn_completed_seen,
            "usage_seen": streamed.usage_seen,
            "candidate_seen": streamed.candidate_seen,
            "output_file_seen": streamed.output_file_seen,
            "validator_started": False,
            "validator_completed": False,
        },
        "answer": answer,
    }


def public_result(
    *, case: dict[str, Any], arm: dict[str, Any], fingerprint: str,
    attempts: list[dict[str, Any]], validation: dict[str, Any],
    router_arm: str | None, router_compute_ms: float, router_preflight_ms: float,
    execution_metadata: dict[str, Any] | None = None,
    execution_fingerprint_value: str | None = None,
    execution_controls: dict[str, Any] | None = None,
) -> dict[str, Any]:
    usage = {key: sum(attempt["usage"][key] for attempt in attempts) for key in ("input_tokens", "reasoning_tokens", "output_tokens", "cached_tokens", "cache_write_tokens")}
    final = attempts[-1]
    estimated_cost = sum(estimate_cost(attempt["usage"], model_pricing(arm["model"])) for attempt in attempts)
    execution_success = bool(final["execution_success"])
    task_success = execution_success and validation["validator_success"] and validation["safety_passed"] and validation["evidence_complete"]
    semantic_quality = None if case["validator"].get("requires_semantic_review") else (5.0 if task_success else 0.0)
    expected_identity = (
        {key: execution_metadata.get(key) for key in (
            "codex_cli_version", "codex_executable_sha256", "codex_distribution_source",
            "vscode_extension_version",
        )}
        if execution_metadata else None
    )
    identity_match = final.get("executable_identity") == expected_identity
    record = {
        "event_type": "result",
        "key": f'{case["case_id"]}:{arm["arm_id"]}',
        "case_id": case["case_id"],
        "category": case["category"],
        "arm_id": arm["arm_id"],
        "model": arm["model"],
        "reasoning_effort": arm["reasoning_effort"],
        "execution_success": execution_success,
        "task_success": task_success,
        "validator_success": validation["validator_success"],
        "evidence_complete": validation["evidence_complete"],
        "semantic_quality": semantic_quality,
        "safety_passed": validation["safety_passed"],
        **usage,
        "latency_ms": round(sum(float(attempt["latency_ms"]) for attempt in attempts) + router_preflight_ms, 3),
        "estimated_cost_usd": round(estimated_cost, 9),
        "retry_count": max(0, len(attempts) - 1),
        "fallback_count": 0,
        "tool_calls": sum(int(attempt["tool_calls"]) for attempt in attempts),
        "unique_files_read": sum(int(attempt["unique_files_read"]) for attempt in attempts),
        "files_modified": validation["files_modified"],
        "router_compute_ms": round(router_compute_ms, 6),
        "router_preflight_ms": round(router_preflight_ms, 6),
        "router_prompt_overhead_tokens": 0,
        "current_router_arm": router_arm,
        "requested_model": arm["model"],
        "requested_reasoning_effort": arm["reasoning_effort"],
        "effective_model": final.get("effective_model"),
        "effective_reasoning_effort": final.get("effective_reasoning_effort"),
        "effective_model_evidence": (
            "runtime_event" if final.get("effective_model") else "requested_and_configured"
        ),
        "effective_reasoning_effort_evidence": (
            "runtime_event" if final.get("effective_reasoning_effort") else "requested_and_configured"
        ),
        "usage_available": bool(final.get("usage_available")),
        "precheck_success": bool(validation["safety_passed"]),
        "outcome_validation_success": validation["validator_success"] if execution_success else None,
        "semantic_review_state": (
            "not_required" if not case["validator"].get("requires_semantic_review")
            else "pending" if execution_success and final["answer"] else "not_started_no_candidate"
        ),
        "execution_backend": "codex-cli-native",
        "execution_backend_executable": final.get("backend_executable"),
        "execution_backend_cwd": final.get("backend_cwd"),
        "execution_backend_contract_sha256": final.get("backend_contract_sha256"),
        "execution_event_types": final.get("backend_event_types", []),
        "execution_stdout_sha256": final.get("stdout_sha256"),
        "execution_stdout_chars": final.get("stdout_chars"),
        "execution_stderr_sha256": final.get("stderr_sha256"),
        "execution_stderr_chars": final.get("stderr_chars"),
        "execution_non_json_stdout_lines": final.get("non_json_stdout_lines"),
        "execution_failure_category": final.get("failure_category"),
        "execution_lifecycle": final.get("lifecycle", {}),
        "last_successful_lifecycle_stage": next(
            (
                stage for stage in reversed((
                    "process_spawned", "codex_process_started", "turn_started_seen",
                    "turn_completed_seen", "usage_seen", "candidate_seen", "output_file_seen",
                    "validator_started", "validator_completed",
                ))
                if final.get("lifecycle", {}).get(stage)
            ),
            None,
        ),
        "execution_runtime_metadata": execution_metadata,
        "execution_fingerprint": execution_fingerprint_value,
        "execution_spawn_identity": final.get("executable_identity"),
        "execution_identity_match": identity_match,
        "execution_controls": execution_controls,
        "experiment_variable_contamination": not bool(
            execution_controls
            and execution_controls.get("clean_fixture")
            and execution_controls.get("user_config_ignored")
            and execution_controls.get("repo_rules_ignored")
            and not execution_controls.get("agents_or_project_config_found")
            and execution_controls.get("availability_fallback_disabled")
            and execution_controls.get("max_retries") == 0
            and execution_controls.get("model_effort_only_variable")
            and identity_match
        ),
        "blind_label": blind_label(fingerprint, case["case_id"], arm["arm_id"]),
        "validator_details": {key: value for key, value in validation.items() if key != "changed_files"},
        "prompt_sha256": hashlib.sha256(case_prompt(case, load_protocol()).encode("utf-8")).hexdigest(),
        "answer_sha256": hashlib.sha256(final["answer"].encode("utf-8")).hexdigest() if final["answer"] else None,
        "answer_chars": len(final["answer"]),
        "stores_prompt": False,
        "stores_answer": False,
        "stores_code": False,
        "stores_tool_arguments": False,
        "cache_state": load_protocol()["cache_state"],
        "experiment_fingerprint": fingerprint,
        "timestamp": datetime.now(UTC).isoformat(),
        "execution_error": final["execution_error"],
        "execution_diagnostic": final.get("execution_diagnostic"),
    }
    missing = REQUIRED_RESULT_FIELDS - record.keys()
    if missing:
        raise AssertionError(f"Result missing fields: {sorted(missing)}")
    return record


def validate_only() -> dict[str, Any]:
    cases, arms, protocol = load_cases(), load_arms(), load_protocol()
    expected_counts = {
        "mechanical": 5, "single_file_coding": 6, "multi_file_tool_use": 6,
        "debugging": 5, "architecture_semantic": 4, "high_risk_read_only": 4,
    }
    errors: list[str] = []
    ids = [case.get("case_id") for case in cases]
    if len(cases) != 30 or len(set(ids)) != 30:
        errors.append("case corpus must contain 30 unique case_id values")
    if Counter(case.get("category") for case in cases) != Counter(expected_counts):
        errors.append("category counts differ from protocol")
    required_case = {"case_id", "category", "task", "fixture_id", "tools", "risk_class", "validator", "acceptance_criteria", "semantic_rubric", "high_risk_safety_envelope", "notes", "execution_policy"}
    for case in cases:
        missing = required_case - case.keys()
        if missing:
            errors.append(f'{case.get("case_id")}: missing {sorted(missing)}')
            continue
        if case["fixture_id"] not in FIXTURES:
            errors.append(f'{case["case_id"]}: missing fixture')
        if "expected_tier" in case or "route_tier" in case:
            errors.append(f'{case["case_id"]}: router label cannot be ground truth')
        envelope = case["high_risk_safety_envelope"]
        if case["risk_class"] == "high" and (envelope["mode"] != "read-only" or envelope["mutation_allowed"]):
            errors.append(f'{case["case_id"]}: high-risk case must be read-only')
        if envelope["mode"] == "read-only" and "answer.md" in case["task"].lower():
            errors.append(f'{case["case_id"]}: read-only task must request final response, not a file write')
        target = case["validator"]["target"]
        known = target in HIDDEN_TESTS or target in MECHANICAL_EXPECTED or target in SEMANTIC_EVIDENCE or target in {"mech-retention-summary", "single-cli-exit-codes", "single-leap-tests"}
        if not known:
            errors.append(f'{case["case_id"]}: unknown validator target {target}')
    core_expected = [
        ("gpt-6-luna", "none"), ("gpt-6-luna", "low"),
        ("gpt-6.1-sol", "low"), ("gpt-6.1-sol", "medium"),
        ("gpt-6-astra", "medium"), ("gpt-6-astra", "high"),
    ]
    if [(arm["model"], arm["reasoning_effort"]) for arm in arms] != core_expected:
        errors.append("core arms differ from protocol")
    pricing = load_pricing_snapshot()
    for arm in [*arms, *load_arms(include_optional=True)]:
        model = pricing.get("models", {}).get(arm["model"])
        if model is None:
            errors.append(f'{arm["arm_id"]}: model missing from experiment pricing snapshot')
        elif arm["reasoning_effort"] not in model.get("supported_reasoning_efforts", []):
            errors.append(f'{arm["arm_id"]}: effort unsupported by experiment pricing snapshot')
    if int(protocol["input_token_reservation_ceiling"]) > 272000:
        errors.append("pilot reservation exceeds pricing snapshot short-context band")
    for schema in (HERE / "schema").glob("*.json"):
        try:
            read_json(schema)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid schema {schema.name}: {exc}")
    if len(FIXTURES) != 30 or set(FIXTURES) != {case["fixture_id"] for case in cases}:
        errors.append("fixture set must exactly match case fixture_id values")
    if protocol["cache_state"] not in {"cold", "warm"}:
        errors.append("cache_state must be explicit")
    for case_id, source in HIDDEN_TESTS.items():
        try:
            compile(source, f"hidden-validator:{case_id}", "exec")
        except SyntaxError as exc:
            errors.append(f"{case_id}: hidden validator does not compile: {exc}")
    for fixture_id, files in FIXTURES.items():
        for relative, source in files.items():
            if relative.endswith(".py"):
                try:
                    compile(source, f"fixture:{fixture_id}:{relative}", "exec")
                except SyntaxError as exc:
                    errors.append(f"{fixture_id}/{relative}: fixture does not compile: {exc}")
    legacy_prompts: set[str] = set()
    router_cases = ROOT / "evals" / "router-v2" / "cases.jsonl"
    if router_cases.exists():
        for line in router_cases.read_text(encoding="utf-8").splitlines():
            legacy = json.loads(line)
            value = legacy.get("input") or (legacy.get("request") or {}).get("input")
            if isinstance(value, str):
                legacy_prompts.add(value.strip())
    try:
        from evals.token_optimization.cases import CASES as legacy_token_cases

        legacy_prompts.update(item.prompt.strip() for item in legacy_token_cases)
    except ImportError:
        errors.append("could not load token_optimization corpus for exact-overlap check")
    overlap = sorted(case["case_id"] for case in cases if case["task"].strip() in legacy_prompts)
    if overlap:
        errors.append(f"new case prompts exactly overlap legacy corpora: {overlap}")
    return {
        "mode": "validate-only",
        "passed": not errors,
        "cases": len(cases),
        "category_counts": dict(Counter(case["category"] for case in cases)),
        "core_arms": len(arms),
        "fixtures": len(FIXTURES),
        "semantic_review_cases": sum(bool(case["validator"].get("requires_semantic_review")) for case in cases),
        "errors": errors,
    }


def dry_run(args: argparse.Namespace) -> dict[str, Any]:
    cases, arms, protocol = selected_experiment(args)
    fingerprint, _components = experiment_fingerprint(cases, arms, protocol, args.seed)
    events = load_events(args.results, fingerprint)
    done = completed_keys(events)
    plan = ordered_plan(cases, arms, args.seed)
    pending = [(case, arm) for case, arm in plan if f'{case["case_id"]}:{arm["arm_id"]}' not in done]
    budget = total_budget_ceiling(cases, arms, protocol)
    return {
        "mode": "dry-run",
        "paid_calls_started": False,
        "experiment_fingerprint": fingerprint,
        "cases": len(cases),
        "arms": len(arms),
        "planned_execution_calls": len(plan),
        "completed_execution_arms": len(done),
        "pending_execution_arms": len(pending),
        "explicit_max_calls": args.max_calls,
        "explicit_max_estimated_usd": args.max_estimated_usd,
        "cache_state": protocol["cache_state"],
        "semantic_review_requires_explicit_output_storage": True,
        "next": [{"case_id": case["case_id"], "arm_id": arm["arm_id"], "reservation_usd": cost_ceiling(arm, protocol)} for case, arm in pending[: max(0, args.max_calls)]],
        "budget_ceiling": budget,
        "privacy": "Results exclude raw prompts, answers, code, tool arguments, and event transcripts by default.",
    }


def exec_contract_preflight(
    *,
    backend: CodexCliBackend,
    launcher: LauncherCandidate,
    case: dict[str, Any],
    arm: dict[str, Any],
    protocol: dict[str, Any],
    work_root: Path,
) -> dict[str, Any]:
    work_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="exec-contract-", dir=work_root) as directory:
        fixture_workspace = Path(directory) / "fixture"
        materialize_fixture(case, fixture_workspace)
        output_path = Path(directory) / "output" / "last-message.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report = backend.preflight_exec_contract(
            CodexExecutionRequest(
                workspace=fixture_workspace,
                prompt=case_prompt(case, protocol),
                model=arm["model"],
                reasoning_effort=arm["reasoning_effort"],
                max_output_tokens=int(protocol["max_output_tokens"]),
                timeout_seconds=int(protocol["timeout_seconds"]),
                read_only=case["high_risk_safety_envelope"]["mode"] == "read-only",
                output_path=output_path,
            ),
            launcher,
            controlled_work_root=work_root,
        )
        return report.public_dict()


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    cases, arms, protocol = selected_experiment(args)
    fingerprint, components = experiment_fingerprint(cases, arms, protocol, args.seed)
    cwd = Path(getattr(args, "preflight_cwd", None) or ROOT).resolve()
    work_root = Path(getattr(args, "work_root", DEFAULT_WORK_ROOT)).resolve()
    backend = CodexCliBackend()
    reports = []
    selected_path = getattr(args, "codex_path", None)
    for arm in arms:
        report = backend.preflight(
            cwd=cwd, model=arm["model"], reasoning_effort=arm["reasoning_effort"], explicit=selected_path,
        )
        item = {"arm_id": arm["arm_id"], **report.public_dict()}
        if report.passed and report.selected is not None:
            item["exec_contract"] = exec_contract_preflight(
                backend=backend,
                launcher=report.selected,
                case=cases[0],
                arm=arm,
                protocol=protocol,
                work_root=work_root,
            )
        reports.append(item)
        if not report.passed or not item.get("exec_contract", {}).get("passed"):
            break
        selected_path = report.selected.path if report.selected else selected_path
    contract_identity = reports[-1].get("exec_contract", {}).get("executable_identity") if reports else None
    execution_metadata = (
        runtime_execution_metadata(contract_identity, components["execution_contract_sha256"])
        if contract_identity else None
    )
    return {
        "mode": "preflight",
        "passed": len(reports) == len(arms) and all(
            item["passed"] and item.get("exec_contract", {}).get("passed") for item in reports
        ),
        "model_calls_started": 0,
        "experiment_fingerprint": fingerprint,
        "execution_contract_sha256": components["execution_contract_sha256"],
        "execution_runtime_metadata": execution_metadata,
        "execution_fingerprint": (
            runtime_execution_fingerprint(fingerprint, execution_metadata)
            if execution_metadata else None
        ),
        "cases_selected": len(cases),
        "arms_selected": len(arms),
        "max_retries": int(protocol["max_retries"]),
        "fallback": "disabled",
        "reports": reports,
    }


def execute(args: argparse.Namespace) -> dict[str, Any]:
    if not args.approve_model_calls:
        raise ValueError("execute requires --approve-model-calls")
    if args.max_calls <= 0 or args.max_estimated_usd <= 0:
        raise ValueError("execute requires positive --max-calls and --max-estimated-usd")
    cases, arms, protocol = selected_experiment(args)
    fingerprint, components = experiment_fingerprint(cases, arms, protocol, args.seed)
    events = load_events(args.results, fingerprint)
    done = completed_keys(events)
    spent = sum(float(event.get("estimated_cost_usd", 0)) for event in events if event.get("event_type") == "result")
    plan = [(case, arm) for case, arm in ordered_plan(cases, arms, args.seed) if f'{case["case_id"]}:{arm["arm_id"]}' not in done]
    backend = CodexCliBackend()
    preflight_reports = []
    launcher: LauncherCandidate | None = None
    selected_path = args.codex_path
    for arm in arms:
        checked = backend.preflight(
            cwd=ROOT, model=arm["model"], reasoning_effort=arm["reasoning_effort"], explicit=selected_path,
        )
        preflight_reports.append({"arm_id": arm["arm_id"], **checked.public_dict()})
        if not checked.passed or checked.selected is None:
            return {
                "mode": "execute", "preflight_passed": False,
                "model_attempts_now": 0, "completed_arms_now": 0, "model_calls_started": 0,
                "preflight": preflight_reports, "blocked_reason": "execution_backend_preflight_failed",
            }
        launcher = checked.selected
        selected_path = launcher.path
    assert launcher is not None
    args.work_root.mkdir(parents=True, exist_ok=True)
    contract_reports = []
    for arm in arms:
        contract_report = exec_contract_preflight(
            backend=backend,
            launcher=launcher,
            case=cases[0],
            arm=arm,
            protocol=protocol,
            work_root=args.work_root,
        )
        contract_reports.append({"arm_id": arm["arm_id"], **contract_report})
        if not contract_report["passed"]:
            return {
                "mode": "execute", "preflight_passed": False,
                "model_attempts_now": 0, "completed_arms_now": 0, "model_calls_started": 0,
                "preflight": preflight_reports, "exec_contract_preflight": contract_reports,
                "blocked_reason": "exec_contract_preflight_failed",
            }
    contract_identity = contract_reports[-1].get("executable_identity")
    if not contract_identity:
        return {
            "mode": "execute", "preflight_passed": False,
            "model_attempts_now": 0, "completed_arms_now": 0, "model_calls_started": 0,
            "preflight": preflight_reports, "exec_contract_preflight": contract_reports,
            "blocked_reason": "executable_identity_missing",
        }
    execution_metadata = runtime_execution_metadata(
        contract_identity, components["execution_contract_sha256"],
    )
    execution_fingerprint_value = runtime_execution_fingerprint(fingerprint, execution_metadata)
    execution_controls = {
        "environment": "controlled_codex_execution",
        "clean_fixture": True,
        "user_config_ignored": all(report.get("user_config_isolated") for report in contract_reports),
        "repo_rules_ignored": all(
            "--ignore-rules" in report.get("command", {}).get("args", [])
            for report in contract_reports
        ),
        "agents_or_project_config_found": any(
            report.get("repo_instruction_contamination") for report in contract_reports
        ),
        "availability_fallback_disabled": True,
        "max_retries": int(protocol["max_retries"]),
        "max_execution_calls": int(args.max_calls),
        "model_effort_only_variable": True,
        "interactive_user_defaults_represented": False,
    }
    completed = 0
    attempts_used = 0
    blocked_reason: str | None = None
    for case, arm in plan:
        if case["validator"].get("requires_semantic_review") and not args.store_outputs:
            blocked_reason = (
                "semantic arm reached without --store-outputs; raw output persistence must be explicitly authorized "
                "before building the blind review queue"
            )
            break
        reservation = cost_ceiling(arm, protocol) * (int(protocol["max_retries"]) + 1)
        if attempts_used >= args.max_calls or spent + reservation > args.max_estimated_usd:
            break
        key = f'{case["case_id"]}:{arm["arm_id"]}'
        append_event(args.results, {
            "event_type": "reservation", "key": key, "case_id": case["case_id"], "arm_id": arm["arm_id"],
            "reserved_cost_usd": reservation, "experiment_fingerprint": fingerprint,
            "execution_fingerprint": execution_fingerprint_value,
            "execution_runtime_metadata": execution_metadata,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        router_arm, router_compute_ms, router_preflight_ms = current_router_arm(case, arms)
        attempts: list[dict[str, Any]] = []
        final_validation: dict[str, Any] | None = None
        final_workspace: Path | None = None
        for retry in range(int(protocol["max_retries"]) + 1):
            if attempts_used >= args.max_calls:
                break
            workspace = args.work_root / f'{case["case_id"]}-{arm["arm_id"]}-{uuid.uuid4().hex[:10]}'
            materialize_fixture(case, workspace)
            before = snapshot_workspace(workspace)
            attempt = run_attempt(case, arm, protocol, workspace, backend, launcher)
            attempts_used += 1
            attempt["lifecycle"]["validator_started"] = True
            try:
                attempt["validation"] = validate_case(case, workspace, attempt["answer"], before)
            except Exception as exc:  # noqa: BLE001 - any validator failure must produce a durable failed result.
                attempt["validation"] = {
                    "validator_success": False,
                    "safety_passed": False,
                    "evidence_complete": False,
                    "files_modified": 0,
                    "validation_reason": f"validator_exception:{type(exc).__name__}",
                    "missing_evidence": ["validator_completed_without_exception"],
                    "changed_files": [],
                }
            finally:
                attempt["lifecycle"]["validator_completed"] = True
            attempts.append(attempt)
            final_validation = attempt["validation"]
            final_workspace = workspace
            if attempt["execution_success"] or not final_validation["safety_passed"]:
                break
            remove_workspace(workspace, args.work_root)
            final_workspace = None
        if not attempts or final_validation is None:
            break
        final_validation = {
            **final_validation,
            "safety_passed": all(attempt["validation"]["safety_passed"] for attempt in attempts),
            "files_modified": sum(int(attempt["validation"]["files_modified"]) for attempt in attempts),
        }
        record = public_result(
            case=case, arm=arm, fingerprint=fingerprint, attempts=attempts,
            validation=final_validation, router_arm=router_arm,
            router_compute_ms=router_compute_ms, router_preflight_ms=router_preflight_ms,
            execution_metadata=execution_metadata,
            execution_fingerprint_value=execution_fingerprint_value,
            execution_controls=execution_controls,
        )
        if args.store_outputs and attempts[-1]["answer"]:
            output_path = args.results.parent / "outputs" / fingerprint / case["case_id"] / f'{record["blind_label"]}.txt'
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(attempts[-1]["answer"], encoding="utf-8")
            record["stores_answer"] = True
            record["output_path"] = str(output_path)
        append_event(args.results, record)
        spent += record["estimated_cost_usd"]
        completed += 1
        if attempts[-1].get("infrastructure_error"):
            blocked_reason = attempts[-1]["execution_error"]
            if final_workspace is not None:
                remove_workspace(final_workspace, args.work_root)
                final_workspace = None
            break
        if final_workspace is not None:
            remove_workspace(final_workspace, args.work_root)
    return {
        "mode": "execute", "experiment_fingerprint": fingerprint,
        "execution_fingerprint": execution_fingerprint_value,
        "execution_runtime_metadata": execution_metadata,
        "completed_arms_now": completed, "model_attempts_now": attempts_used,
        "model_calls_started": attempts_used,
        "cumulative_estimated_cost_usd": round(spent, 9),
        "results": str(args.results), "stores_outputs": bool(args.store_outputs),
        "blocked_reason": blocked_reason, "preflight_passed": True, "preflight": preflight_reports,
        "exec_contract_preflight": contract_reports,
    }


def load_reviews(
    path: Path,
    fingerprint: str,
    cases: list[dict[str, Any]],
    arms: list[dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    reviews: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    if not path.exists():
        return reviews
    labels = {
        (case["case_id"], blind_label(fingerprint, case["case_id"], arm["arm_id"])): arm["arm_id"]
        for case in cases for arm in arms
    }
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            review = json.loads(line)
            case_id = str(review["case_id"])
            arm_id = labels[(case_id, str(review["blind_label"]))]
            reviews[(case_id, arm_id)].append(review)
        except (json.JSONDecodeError, KeyError):
            continue
    return reviews


def review_plan(args: argparse.Namespace) -> dict[str, Any]:
    cases, arms, protocol = selected_experiment(args)
    fingerprint, _components = experiment_fingerprint(cases, arms, protocol, args.seed)
    case_by_id = {case["case_id"]: case for case in cases}
    human_sample = human_review_sample_keys(cases, arms, float(protocol["human_review_sample_rate"]), args.seed)
    records = [event for event in load_events(args.results, fingerprint) if event.get("event_type") == "result"]
    entries = []
    for record in records:
        case = case_by_id[record["case_id"]]
        if not case["validator"].get("requires_semantic_review"):
            continue
        entries.append({
            "case_id": case["case_id"],
            "category": case["category"],
            "blind_label": record["blind_label"],
            "task": case["task"],
            "acceptance_criteria": case["acceptance_criteria"],
            "semantic_rubric": case["semantic_rubric"],
            "answer_path": record.get("output_path"),
            "output_available": bool(record.get("stores_answer") and record.get("output_path")),
            "random_human_sample": (case["case_id"], record["arm_id"]) in human_sample,
        })
    random.Random(args.seed).shuffle(entries)
    args.review_plan.parent.mkdir(parents=True, exist_ok=True)
    args.review_plan.write_text("".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries), encoding="utf-8")
    return {
        "mode": "review-plan", "experiment_fingerprint": fingerprint,
        "blind_entries": len(entries), "outputs_available": sum(entry["output_available"] for entry in entries),
        "plan": str(args.review_plan), "reveals_arm_identity": False,
    }


def _parse_judge_json(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    value = json.loads(candidate)
    score = float(value["score"])
    if not 1 <= score <= 5:
        raise ValueError("judge score outside 1..5")
    return {
        "score": score,
        "rubric_passed": bool(value["rubric_passed"]),
        "borderline": bool(value["borderline"]),
    }


def run_judge_attempt(
    entry: dict[str, Any],
    answer: str,
    protocol: dict[str, Any],
    codex_path: str,
) -> dict[str, Any]:
    prompt = (
        "You are a strict blind rubric judge. The candidate identity is opaque. Do not infer model or effort. "
        "Score correctness, completeness, instruction following, safety, evidence quality, and useful concision. "
        "Return JSON only with score (1..5), rubric_passed (boolean), and borderline (boolean).\n\n"
        f"TASK:\n{entry['task']}\n\nACCEPTANCE:\n"
        + "\n".join(f"- {item}" for item in entry["acceptance_criteria"])
        + "\n\nRUBRIC:\n"
        + "\n".join(f"- {item}" for item in entry["semantic_rubric"])
        + f"\n\nCANDIDATE {entry['blind_label']}:\n{answer}"
    )
    with tempfile.TemporaryDirectory(prefix="adaptive-reasoning-judge-") as directory:
        workspace = Path(directory) / "workspace"
        workspace.mkdir()
        answer_path = Path(directory) / "judge-result.txt"
        command = [
            codex_path, "exec", "--json", "--ephemeral", "--skip-git-repo-check",
            "--sandbox", "read-only", "--color", "never", "-C", str(workspace),
            "-m", protocol["judge_model"], "-c", 'model_provider="openai"',
            "-c", f'model_reasoning_effort="{protocol["judge_reasoning_effort"]}"',
            "-c", f'model_max_output_tokens={int(protocol["judge_max_output_tokens"])}',
            "-c", 'approval_policy="never"', "-c", 'default_permissions=":read-only"',
            "--output-last-message", str(answer_path), "-",
        ]
        started = time.perf_counter()
        streamed = run_streaming_process(
            command,
            input_text=prompt,
            cwd=workspace,
            env=subscription_environment(),
            timeout_seconds=int(protocol["timeout_seconds"]),
            file_limit=0,
            tool_call_limit=0,
        )
        output = answer_path.read_text(encoding="utf-8") if answer_path.exists() else ""
    usage = normalize_usage(streamed.usage)
    infra_error = infrastructure_error(streamed.stop_reason, streamed.returncode, streamed.stderr)
    error = None if streamed.returncode == 0 and streamed.stop_reason is None else (infra_error or streamed.stop_reason or f"codex_exit_{streamed.returncode}")
    verdict = None
    if error is None:
        try:
            verdict = _parse_judge_json(output)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            error = "invalid_judge_json"
    return {
        "success": error is None,
        "error": error,
        "infrastructure_error": infra_error is not None,
        "verdict": verdict,
        "usage": usage,
        "latency_ms": (time.perf_counter() - started) * 1000,
    }


def judge(args: argparse.Namespace) -> dict[str, Any]:
    if not args.approve_model_calls:
        raise ValueError("judge requires --approve-model-calls")
    if args.max_calls <= 0 or args.max_estimated_usd <= 0:
        raise ValueError("judge requires positive --max-calls and --max-estimated-usd")
    cases, arms, protocol = selected_experiment(args)
    fingerprint, _components = experiment_fingerprint(cases, arms, protocol, args.seed)
    case_by_id = {case["case_id"]: case for case in cases}
    records = [event for event in load_events(args.results, fingerprint) if event.get("event_type") == "result"]
    review_events = load_events(args.reviews, fingerprint)
    completed = {
        str(event["blind_label"])
        for event in review_events
        if event.get("event_type") == "semantic_review" and event.get("reviewer_type") == "blind_judge"
    }
    spent = sum(float(event.get("estimated_cost_usd", 0)) for event in review_events)
    entries = []
    for record in records:
        case = case_by_id[record["case_id"]]
        if not case["validator"].get("requires_semantic_review") or record["blind_label"] in completed:
            continue
        output_path = Path(str(record.get("output_path") or ""))
        if not record.get("stores_answer") or not output_path.is_file():
            continue
        entries.append({
            "case_id": case["case_id"], "blind_label": record["blind_label"],
            "task": case["task"], "acceptance_criteria": case["acceptance_criteria"],
            "semantic_rubric": case["semantic_rubric"], "answer_path": output_path,
        })
    random.Random(args.seed).shuffle(entries)
    executable = find_codex(args.codex_path)
    login = codex_login_status(executable)
    if not login.get("available") or not login.get("chatgpt_login"):
        raise RuntimeError("Codex ChatGPT login is required; API-key billing is never enabled implicitly")
    calls = 0
    completed_now = 0
    judge_arm = {"model": protocol["judge_model"]}
    for entry in entries:
        reservation = cost_ceiling(judge_arm, protocol, judge=True) * (int(protocol["max_retries"]) + 1)
        if calls >= args.max_calls or spent + reservation > args.max_estimated_usd:
            break
        append_event(args.reviews, {
            "event_type": "judge_reservation", "case_id": entry["case_id"],
            "blind_label": entry["blind_label"], "reserved_cost_usd": reservation,
            "experiment_fingerprint": fingerprint, "timestamp": datetime.now(UTC).isoformat(),
        })
        attempts = []
        answer = entry["answer_path"].read_text(encoding="utf-8")
        for _retry in range(int(protocol["max_retries"]) + 1):
            if calls >= args.max_calls:
                break
            attempt = run_judge_attempt(entry, answer, protocol, executable)
            attempts.append(attempt)
            calls += 1
            if attempt["success"]:
                break
        cost = sum(estimate_cost(attempt["usage"], model_pricing(protocol["judge_model"])) for attempt in attempts)
        spent += cost
        final = attempts[-1] if attempts else None
        if final and final["success"]:
            verdict = final["verdict"]
            append_event(args.reviews, {
                "event_type": "semantic_review", "case_id": entry["case_id"],
                "blind_label": entry["blind_label"], "reviewer_id": "blind-judge-v1",
                "reviewer_type": "blind_judge", **verdict,
                "retry_count": len(attempts) - 1,
                "latency_ms": round(sum(attempt["latency_ms"] for attempt in attempts), 3),
                "estimated_cost_usd": round(cost, 9), "experiment_fingerprint": fingerprint,
                "timestamp": datetime.now(UTC).isoformat(),
            })
            completed_now += 1
        else:
            append_event(args.reviews, {
                "event_type": "judge_failure", "case_id": entry["case_id"],
                "blind_label": entry["blind_label"], "execution_error": final["error"] if final else "max_calls",
                "retry_count": max(0, len(attempts) - 1), "estimated_cost_usd": round(cost, 9),
                "experiment_fingerprint": fingerprint, "timestamp": datetime.now(UTC).isoformat(),
            })
            if final and final.get("infrastructure_error"):
                break
    return {
        "mode": "judge", "experiment_fingerprint": fingerprint,
        "blind_reviews_completed_now": completed_now, "model_attempts_now": calls,
        "cumulative_estimated_cost_usd": round(spent, 9), "reviews": str(args.reviews),
        "stores_judge_prompt_or_answer": False,
    }


def human_review_sample_keys(
    cases: list[dict[str, Any]],
    arms: list[dict[str, Any]],
    rate: float,
    seed: int,
) -> set[tuple[str, str]]:
    pairs = [
        (case["case_id"], arm["arm_id"])
        for case in cases if case["validator"].get("requires_semantic_review")
        for arm in arms
    ]
    random.Random(seed).shuffle(pairs)
    return set(pairs[: math.ceil(len(pairs) * rate)])


def choose_lowest_sufficient(rows: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any] | None:
    sufficient = [row for row in rows if row.get("sufficient")]
    if not sufficient:
        return None
    minimum_cost = min(float(row["estimated_cost_usd"]) for row in sufficient)
    close = [
        row for row in sufficient
        if float(row["estimated_cost_usd"]) - minimum_cost
        <= max(float(protocol["cost_close_absolute_usd"]), minimum_cost * float(protocol["cost_close_relative"]))
    ]
    return min(close, key=lambda row: (float(row["latency_ms"]), int(row["compute_rank"])))


def is_sufficient(row: dict[str, Any], best_quality: float | None, protocol: dict[str, Any]) -> bool:
    quality = row.get("semantic_quality")
    return bool(
        row.get("execution_success")
        and row.get("validator_success")
        and row.get("safety_passed")
        and row.get("evidence_complete")
        and quality is not None
        and row.get("semantic_rubric_passed", True)
        and (not row.get("human_review_required") or row.get("human_review_complete"))
        and float(quality) >= float(protocol["semantic_absolute_threshold"])
        and best_quality is not None
        and best_quality - float(quality) <= float(protocol["semantic_best_arm_max_gap"])
    )


def pairwise_sensitivity(by_case: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    comparisons = {
        "effort_luna_none_to_low": ("luna-none", "luna-low"),
        "effort_sol_low_to_medium": ("sol-low", "sol-medium"),
        "effort_sol_medium_to_high": ("sol-medium", "sol-high"),
        "model_luna_to_sol_at_low": ("luna-low", "sol-low"),
        "model_sol_to_astra_at_medium": ("sol-medium", "astra-medium"),
    }
    result: dict[str, Any] = {}
    for name, (lower, higher) in comparisons.items():
        pairs = []
        for rows in by_case.values():
            indexed = {row["arm_id"]: row for row in rows}
            if lower in indexed and higher in indexed:
                pairs.append((indexed[lower], indexed[higher]))
        result[name] = {
            "paired_cases": len(pairs),
            "task_success_gained": sum(not bool(low.get("task_success")) and bool(high.get("task_success")) for low, high in pairs),
            "task_success_lost": sum(bool(low.get("task_success")) and not bool(high.get("task_success")) for low, high in pairs),
            "sufficiency_gained": sum(not bool(low.get("sufficient")) and bool(high.get("sufficient")) for low, high in pairs),
            "mean_cost_delta_usd": statistics.mean(
                float(high["estimated_cost_usd"]) - float(low["estimated_cost_usd"])
                for low, high in pairs
            ) if pairs else None,
            "mean_semantic_delta": statistics.mean(
                float(high["semantic_quality"]) - float(low["semantic_quality"])
                for low, high in pairs
                if high.get("semantic_quality") is not None and low.get("semantic_quality") is not None
            ) if any(high.get("semantic_quality") is not None and low.get("semantic_quality") is not None for low, high in pairs) else None,
        }
    return result


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    cases, arms, protocol = selected_experiment(args)
    fingerprint, _components = experiment_fingerprint(cases, arms, protocol, args.seed)
    arm_by_id = {arm["arm_id"]: arm for arm in arms}
    case_by_id = {case["case_id"]: case for case in cases}
    events = load_events(args.results, fingerprint)
    records = [event for event in events if event.get("event_type") == "result"]
    reviews = load_reviews(args.reviews, fingerprint, cases, arms)
    human_sample = human_review_sample_keys(cases, arms, float(protocol["human_review_sample_rate"]), args.seed)
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in records:
        row = dict(source)
        row["compute_rank"] = arm_by_id[row["arm_id"]]["compute_rank"]
        semantic_reviews = reviews.get((row["case_id"], row["arm_id"]), [])
        semantic_required = bool(case_by_id[row["case_id"]]["validator"].get("requires_semantic_review"))
        if semantic_reviews:
            scores = [float(review["score"]) for review in semantic_reviews]
            row["semantic_quality"] = statistics.mean(scores)
            row["semantic_rubric_passed"] = all(bool(review.get("rubric_passed")) for review in semantic_reviews)
            row["semantic_disagreement"] = max(scores) - min(scores) if len(scores) > 1 else 0.0
            row["semantic_borderline"] = any(bool(review.get("borderline")) for review in semantic_reviews)
        else:
            row["semantic_rubric_passed"] = not semantic_required
            row["semantic_disagreement"] = 0.0
            row["semantic_borderline"] = False
        row["human_review_required"] = semantic_required and (
            row["semantic_borderline"]
            or row["semantic_disagreement"] > 0.5
            or (row["case_id"], row["arm_id"]) in human_sample
        )
        row["human_review_complete"] = any(review.get("reviewer_type") == "human" for review in semantic_reviews)
        by_case[row["case_id"]].append(row)

    case_reports: list[dict[str, Any]] = []
    classification_errors: list[dict[str, Any]] = []
    for case_id, case in case_by_id.items():
        rows = by_case.get(case_id, [])
        base_eligible = [
            row for row in rows
            if row.get("execution_success") and row.get("validator_success")
            and row.get("safety_passed") and row.get("evidence_complete")
            and row.get("semantic_quality") is not None
            and row.get("semantic_rubric_passed")
            and (not row.get("human_review_required") or row.get("human_review_complete"))
        ]
        best_quality = max((float(row["semantic_quality"]) for row in base_eligible), default=None)
        for row in rows:
            row["sufficient"] = is_sufficient(row, best_quality, protocol)
            row["router_overhead_share"] = (
                float(row["router_preflight_ms"]) / float(row["latency_ms"])
                if float(row["latency_ms"]) > 0 else 0.0
            )
        lowest = choose_lowest_sufficient(rows, protocol)
        current = next((row.get("current_router_arm") for row in rows if row.get("current_router_arm")), None)
        comparison = "unresolved"
        if lowest and current in arm_by_id:
            current_rank = arm_by_id[current]["compute_rank"]
            lowest_rank = arm_by_id[lowest["arm_id"]]["compute_rank"]
            comparison = "exact" if current == lowest["arm_id"] else "over-route" if current_rank > lowest_rank else "under-route"
            if comparison != "exact":
                classification_errors.append({"case_id": case_id, "category": case["category"], "comparison": comparison, "current_router_arm": current, "lowest_sufficient_arm": lowest["arm_id"]})
        case_reports.append({
            "case_id": case_id, "category": case["category"], "risk_class": case["risk_class"],
            "arm_matrix": rows, "highest_qualified_semantic_quality": best_quality,
            "lowest_sufficient_arm": lowest["arm_id"] if lowest else None,
            "current_layman_router_arm": current, "router_comparison": comparison,
        })

    category_stats: dict[str, Any] = {}
    for category in sorted({case["category"] for case in cases}):
        reports = [report for report in case_reports if report["category"] == category]
        category_stats[category] = {
            "cases": len(reports),
            "resolved": sum(report["lowest_sufficient_arm"] is not None for report in reports),
            "exact": sum(report["router_comparison"] == "exact" for report in reports),
            "over_route": sum(report["router_comparison"] == "over-route" for report in reports),
            "under_route": sum(report["router_comparison"] == "under-route" for report in reports),
        }
    sensitivity: dict[str, Any] = {}
    for dimension in ("model", "reasoning_effort"):
        values: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for rows in by_case.values():
            for row in rows:
                values[str(row[dimension])].append(row)
        sensitivity[dimension] = {
            value: {
                "arms": len(rows),
                "task_success_rate": sum(bool(row.get("task_success")) for row in rows) / len(rows),
                "sufficient_rate": sum(bool(row.get("sufficient")) for row in rows) / len(rows),
                "mean_estimated_cost_usd": statistics.mean(float(row["estimated_cost_usd"]) for row in rows),
            }
            for value, rows in values.items()
        }
    report = {
        "protocol_version": protocol["protocol_version"],
        "experiment_fingerprint": fingerprint,
        "price_version": load_pricing_snapshot()["price_version"],
        "results_loaded": len(records),
        "cases_resolved": sum(report["lowest_sufficient_arm"] is not None for report in case_reports),
        "case_results": case_reports,
        "classification_error_analysis": classification_errors,
        "category_statistics": category_stats,
        "model_vs_effort_sensitivity": sensitivity,
        "paired_model_effort_sensitivity": pairwise_sensitivity(by_case),
        "router_overhead": {
            "mean_share": statistics.mean(
                float(row["router_preflight_ms"]) / float(row["latency_ms"])
                for rows in by_case.values() for row in rows if float(row["latency_ms"]) > 0
            ) if records else None,
            "definition": "offline deterministic Layman classification/preflight only; upstream model latency excluded",
        },
        "human_review_policy": {
            "borderline": "always",
            "judge_disagreement_over_0_5": "always",
            "deterministic_sample_rate": protocol["human_review_sample_rate"],
        },
        "limitations": protocol["analysis_limitations"],
    }
    args.analysis.parent.mkdir(parents=True, exist_ok=True)
    args.analysis.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {key: value for key, value in report.items() if key != "case_results"}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Layman Adaptive Reasoning v1 benchmark")
    subparsers = result.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate-only")
    for name in ("preflight", "dry-run", "execute", "review-plan", "judge", "analyze"):
        command = subparsers.add_parser(name)
        command.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
        command.add_argument("--include-optional", action="store_true")
        command.add_argument("--seed", type=int, default=20260815)
        command.add_argument("--case-id", action="append", default=[])
        command.add_argument("--arm-id", action="append", default=[])
        command.add_argument("--max-retries", type=int)
        command.add_argument("--max-calls", type=int, default=0)
        command.add_argument("--max-estimated-usd", type=float, default=0.0)
        if name in {"preflight", "execute"}:
            command.add_argument("--codex-path")
        if name == "preflight":
            command.add_argument("--preflight-cwd", type=Path)
            command.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
        if name == "execute":
            command.add_argument("--approve-model-calls", action="store_true")
            command.add_argument("--store-outputs", action="store_true")
            command.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
        if name == "analyze":
            command.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
            command.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
        if name == "review-plan":
            command.add_argument(
                "--review-plan",
                type=Path,
                default=ROOT / "build" / "adaptive-reasoning-v1" / "blind-review-plan.jsonl",
            )
        if name == "judge":
            command.add_argument("--approve-model-calls", action="store_true")
            command.add_argument("--codex-path")
            command.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "validate-only":
        result = validate_only()
    elif args.command == "preflight":
        result = preflight(args)
    elif args.command == "dry-run":
        result = dry_run(args)
    elif args.command == "execute":
        result = execute(args)
    elif args.command == "review-plan":
        result = review_plan(args)
    elif args.command == "judge":
        result = judge(args)
    else:
        result = analyze(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("passed", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
