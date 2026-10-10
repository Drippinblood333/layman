from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .classify import _is_inheritance_read_only_intent, classify_task
from .config import load_config
from .execution_control import (
    USAGE_KEYS,
    CancellationToken,
    run_streaming_process,
    usage_from_events,
)
from .models import RouteTier, TaskType
from .plus_eval import (
    _safe_error,
    _usage_from_events,
    codex_login_status,
    event_metrics,
    find_codex,
    subscription_environment,
)
from .project_status import inspect_project
from .prompt_guidance import prompt_guidance
from .routing import decide_route, router_overhead, structured_decision
from .workflow import select_workflow

COMPACT_PROMPT = (
    "Compress the active task history. Preserve the objective, explicit user decisions, current scope, "
    "modified files, test results, unresolved errors, safety constraints, and remaining work. Remove "
    "duplicate logs, superseded exploration, repeated file contents, and already-resolved discussion."
)


@dataclass(frozen=True)
class TierExecutionPolicy:
    initial_files: int
    expanded_files: int
    tool_calls: int
    tool_output_tokens: int
    final_output_token_target: int
    compact_tokens: int
    verbosity: str


POLICIES = {
    RouteTier.FAST: TierExecutionPolicy(3, 6, 12, 2_000, 800, 32_000, "low"),
    RouteTier.BALANCED: TierExecutionPolicy(6, 12, 30, 4_000, 1_500, 48_000, "low"),
    RouteTier.DEEP: TierExecutionPolicy(10, 20, 60, 6_000, 2_500, 64_000, "medium"),
}
PLUS_USAGE_KEYS = USAGE_KEYS


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _usage_available(stdout: str) -> bool:
    return usage_from_events(stdout)[1]


def _text_output(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def _completion_read_only_intent(task: str) -> bool:
    # Scope exclusions do not prohibit work on the requested file. Ignore only
    # these complete clauses when checking completion, never when authorizing
    # execution or passing the original request to Codex.
    remaining = re.sub(
        r"(?:不要|不得)\s*(?:修改|改动)\s*(?:接口|其他文件)(?=\s*(?:$|[,，。;；.!]))|"
        r"\bdo\s+not\s+(?:modify|change)\s+(?:the\s+)?(?:api|interface|other\s+files)"
        r"(?=\s*(?:$|[,;.!]))",
        "",
        task,
        flags=re.IGNORECASE,
    )
    return _is_inheritance_read_only_intent(remaining)


def _execution_contract(tier: RouteTier, policy: TierExecutionPolicy, *, read_only: bool, workflow: str) -> str:
    development_safety = (
        "Keep validation/errors/accessibility; check affected callers. "
        if not read_only and workflow in {"understand-implement-verify", "reproduce-fix-verify", "discover-test-gaps-verify"}
        else ""
    )
    action = (
        "Read-only: analyze; do not modify files."
        if read_only
        else (
            "If implementation is requested, you must edit the workspace and verify now; "
            "no advice-only result or extra proceed question. Make only requested changes."
        )
    )
    return (
        f"Layman {tier.value}/{workflow}. Preserve request/scope. {action} "
        f"Search symbols/tests first; read only completion evidence. {development_safety}"
        f"File ceilings, not targets: {policy.initial_files} initially; {policy.expanded_files} only for a concrete "
        f"evidence gap; at most {policy.tool_calls} tool calls. "
        "Reuse evidence; avoid broad scans, repeated reads and full logs. "
        "Answer briefly: outcome, verification, risks/next step. "
        f"Soft upper guide {policy.final_output_token_target} final-answer tokens; never pad or truncate needed detail."
    )


def _candidate_tiers(selected: RouteTier) -> list[RouteTier]:
    if selected == RouteTier.FAST:
        return [RouteTier.FAST, RouteTier.BALANCED, RouteTier.DEEP]
    if selected == RouteTier.BALANCED:
        return [RouteTier.BALANCED, RouteTier.DEEP]
    return [RouteTier.DEEP]


def plus_task_plan(
    task: str,
    *,
    config: Any | None = None,
    allow_destructive: bool = False,
) -> dict[str, Any]:
    if not task.strip():
        raise ValueError("Task from stdin must not be empty")
    config = config or load_config()
    payload = {"model": "auto", "input": task}
    preflight_started_ns = time.perf_counter_ns()
    feature_started_ns = time.perf_counter_ns()
    features = classify_task(payload, config)
    feature_finished_ns = time.perf_counter_ns()
    policy_started_ns = time.perf_counter_ns()
    decision = decide_route(features, config)
    policy_finished_ns = time.perf_counter_ns()
    policy = POLICIES[decision.route_tier]
    destructive_blocked = features.destructive and not allow_destructive
    guidance = prompt_guidance(task)
    read_only = features.risk == "high" and not (features.destructive and allow_destructive)
    preflight_finished_ns = time.perf_counter_ns()
    feature_extraction_ms = (feature_finished_ns - feature_started_ns) / 1_000_000
    policy_decision_ms = (policy_finished_ns - policy_started_ns) / 1_000_000
    decision = decision.model_copy(update={
        "feature_extraction_ms": feature_extraction_ms,
        "policy_decision_ms": policy_decision_ms,
        "router_compute_ms": feature_extraction_ms + policy_decision_ms,
        "total_routing_preflight_ms": (preflight_finished_ns - preflight_started_ns) / 1_000_000,
    })
    return {
        "route_tier": decision.route_tier.value,
        "model": decision.selected_model,
        "effort": decision.reasoning_effort,
        "route_reason": decision.route_reason,
        "task_type": features.task_type.value,
        "workflow": select_workflow(features.task_type, features.risk),
        "risk": features.risk,
        "destructive": features.destructive,
        "destructive_reason": features.destructive_reason,
        "execution_allowed": not destructive_blocked and not guidance["needs_clarification"],
        "prompt_guidance": guidance,
        "sandbox": "read-only" if read_only else "workspace-write",
        "initial_file_budget": policy.initial_files,
        "expanded_file_budget": policy.expanded_files,
        "tool_call_budget": policy.tool_calls,
        "tool_output_token_limit": policy.tool_output_tokens,
        "final_output_token_target": policy.final_output_token_target,
        "compact_token_limit": policy.compact_tokens,
        "stores_prompt_or_answer": False,
        "routing_decision": structured_decision(decision),
        "router_overhead": router_overhead(decision),
    }


def run_plus_task(
    task: str,
    *,
    cwd: Path,
    codex_path: str | None = None,
    timeout_seconds: int = 1_800,
    execute: bool = True,
    allow_destructive: bool = False,
    max_model_attempts: int | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    cancel_token: CancellationToken | None = None,
) -> dict[str, Any]:
    if max_model_attempts is not None and (
        isinstance(max_model_attempts, bool) or not isinstance(max_model_attempts, int) or max_model_attempts < 1
    ):
        raise ValueError("max_model_attempts must be a positive integer")
    config = load_config()
    preview = plus_task_plan(task, config=config, allow_destructive=allow_destructive)
    workspace = cwd.expanduser().resolve()
    if not workspace.is_dir():
        raise FileNotFoundError(f"Workspace does not exist: {workspace}")
    project = inspect_project(workspace)
    preview["project_stage"] = project["stage"]
    task_type = TaskType(str(preview["task_type"]))
    preview["workflow"] = select_workflow(
        task_type,
        str(preview["risk"]),
        project_stage=project["stage"],
        task=task,
    )
    if not execute:
        return {"mode": "dry-run", **preview}
    if not preview["execution_allowed"]:
        clarification_required = bool(preview["prompt_guidance"]["needs_clarification"])
        return {
            "mode": "run",
            "status": "blocked",
            **preview,
            "attempts": [],
            "usage": {key: 0 for key in PLUS_USAGE_KEYS},
            "usage_incomplete": False,
            "latency_ms": 0,
            "tool_calls": 0,
            "unique_files_read": 0,
            "compactions": 0,
            "fallback_used": False,
            "error_category": "prompt_clarification_required" if clarification_required else "destructive_authorization_required",
            "answer": (
                "\n".join(preview["prompt_guidance"]["questions"]) if clarification_required else
                "Layman blocked this destructive request before starting Codex. "
                "A human must rerun the local CLI with --allow-destructive after reviewing the exact scope."
            ),
        }
    command_runner = runner or subprocess.run
    executable = find_codex(codex_path, runner=command_runner)
    login = codex_login_status(executable, runner=command_runner)
    if not login["available"] or not login["chatgpt_login"]:
        raise RuntimeError("Codex must be logged in with ChatGPT; refusing API-key billing")

    selected = RouteTier(preview["route_tier"])
    started = time.perf_counter()
    attempts: list[dict[str, Any]] = []
    answer = ""
    usage = {key: 0 for key in PLUS_USAGE_KEYS}
    usage_incomplete = False
    aggregate_metrics = {"tool_calls": 0, "unique_files_read": 0, "compactions": 0, "command_failures": 0}
    status = "failed"
    error_category: str | None = None
    final_tier = selected

    candidates = _candidate_tiers(selected)
    if max_model_attempts is not None:
        candidates = candidates[:max_model_attempts]
    for tier in candidates:
        spec = config.tiers[tier]
        policy = POLICIES[tier]
        read_only = preview["sandbox"] == "read-only"
        contract = _execution_contract(tier, policy, read_only=read_only, workflow=str(preview["workflow"]))
        with tempfile.TemporaryDirectory(prefix="layman-auto-") as directory:
            last_message = Path(directory) / "last-message.txt"
            command = [
                executable,
                "exec",
                "--json",
                "--ephemeral",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only" if read_only else "workspace-write",
                "--color",
                "never",
                "-C",
                str(workspace),
                "-m",
                spec.model,
                "-c",
                'model_provider="openai"',
                "-c",
                f'model_reasoning_effort={_toml_string(spec.reasoning_effort)}',
                "-c",
                f'model_verbosity={_toml_string(policy.verbosity)}',
                "-c",
                f"tool_output_token_limit={policy.tool_output_tokens}",
                "-c",
                f"model_auto_compact_token_limit={policy.compact_tokens}",
                "-c",
                'model_auto_compact_token_limit_scope="body_after_prefix"',
                "-c",
                f"compact_prompt={_toml_string(COMPACT_PROMPT)}",
                "-c",
                f"developer_instructions={_toml_string(contract)}",
                "-c",
                'approval_policy="never"',
                "-c",
                f'default_permissions={_toml_string(":read-only" if read_only else ":workspace")}',
                "--output-last-message",
                str(last_message),
                "-",
            ]
            environment = subscription_environment()
            environment["CODEX_PERMISSION_PROFILE"] = ":read-only" if read_only else ":workspace"
            stop_reason: str | None = None
            if runner is None:
                streamed = run_streaming_process(
                    command,
                    input_text=task,
                    cwd=workspace,
                    env=environment,
                    timeout_seconds=timeout_seconds,
                    file_limit=policy.expanded_files,
                    tool_call_limit=policy.tool_calls,
                    cancel_token=cancel_token,
                )
                returncode = streamed.returncode
                stderr = streamed.stderr
                attempt_usage = streamed.usage
                attempt_usage_available = streamed.usage_available
                attempt_metrics = {
                    "tool_calls": streamed.tool_calls,
                    "unique_files_read": streamed.unique_files_read,
                    "compactions": streamed.compactions,
                    "command_failures": streamed.command_failures,
                }
                stop_reason = streamed.stop_reason
            else:
                try:
                    result = runner(
                        command,
                        input=task,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds,
                        check=False,
                        env=environment,
                        cwd=workspace,
                    )
                except subprocess.TimeoutExpired as exc:
                    stdout = _text_output(exc.stdout)
                    attempt_usage = _usage_from_events(stdout)
                    attempt_metrics = event_metrics(stdout)
                    for key in aggregate_metrics:
                        aggregate_metrics[key] += int(attempt_metrics[key])
                    attempts.append({
                        "tier": tier.value,
                        "model": spec.model,
                        "status": "timeout",
                        "usage": attempt_usage,
                        "usage_available": _usage_available(stdout),
                        **attempt_metrics,
                    })
                    for key in PLUS_USAGE_KEYS:
                        usage[key] += attempt_usage[key]
                    usage_incomplete = True
                    error_category = "timeout"
                    final_tier = tier
                    break
                stdout = _text_output(result.stdout)
                returncode = result.returncode
                stderr = _text_output(result.stderr)
                attempt_usage = _usage_from_events(stdout)
                attempt_usage_available = _usage_available(stdout)
                attempt_metrics = event_metrics(stdout)
                if (
                    attempt_metrics["unique_files_read"] > policy.expanded_files
                    or attempt_metrics["tool_calls"] > policy.tool_calls
                ):
                    stop_reason = "budget_exceeded"

            if stop_reason in {"budget_exceeded", "cancelled", "timeout"}:
                error_category = stop_reason
            else:
                error_category = None if returncode == 0 else _safe_error(stderr, returncode)
            if error_category not in {"budget_exceeded", "cancelled", "timeout"}:
                answer = last_message.read_text(encoding="utf-8") if last_message.exists() else ""
            for key in PLUS_USAGE_KEYS:
                usage[key] += attempt_usage[key]
            for key in aggregate_metrics:
                aggregate_metrics[key] += int(attempt_metrics[key])
            attempts.append({
                "tier": tier.value,
                "model": spec.model,
                "status": error_category or "completed",
                "usage": attempt_usage,
                "usage_available": attempt_usage_available,
                **attempt_metrics,
            })
            usage_incomplete = usage_incomplete or not attempt_usage_available or stop_reason is not None
            final_tier = tier
            if error_category is None and returncode == 0:
                status = "completed"
                break
            if error_category in {"budget_exceeded", "cancelled"}:
                status = error_category
                break
            if error_category != "model_unavailable":
                break

    final_spec = config.tiers[final_tier]
    final_policy = POLICIES[final_tier]
    # No actions, or only failed command actions, cannot establish delivery.
    # Other actions avoid this narrow guard but do not prove correctness.
    only_failed_commands = (
        aggregate_metrics["tool_calls"] > 0
        and aggregate_metrics["command_failures"] == aggregate_metrics["tool_calls"]
    )
    if (
        status == "completed"
        and preview["sandbox"] == "workspace-write"
        and preview["task_type"] in {TaskType.NORMAL_CODING.value, TaskType.TESTING.value, TaskType.DOCUMENTATION.value}
        and not _completion_read_only_intent(task)
        and re.search(r"(?:^|[\s`])(?:[\w.-]+/)+[\w.-]+\.(?:py|js|ts|tsx|go|rs|java|md|toml|yaml|yml)\b", task)
        and (aggregate_metrics["tool_calls"] == 0 or only_failed_commands)
    ):
        status = "needs_verification"
        if only_failed_commands:
            error_category = "workspace_command_success_not_observed"
            answer = "观察到的工具操作仅为失败命令，不能确认任务已完成；未自动重试。\n" + answer
        else:
            error_category = "workspace_execution_not_observed"
            answer = "未观察到指定文件的工具操作，不能确认任务已完成；未自动重试。\n" + answer
    return {
        "mode": "run",
        "status": status,
        "route_tier": final_tier.value,
        "model": final_spec.model,
        "effort": final_spec.reasoning_effort,
        "risk": preview["risk"],
        "sandbox": preview["sandbox"],
        "fallback_used": final_tier != selected,
        "attempts": attempts,
        "usage": usage,
        "usage_incomplete": usage_incomplete,
        "latency_ms": round((time.perf_counter() - started) * 1_000),
        **aggregate_metrics,
        "file_budget": {"initial": final_policy.initial_files, "expanded": final_policy.expanded_files},
        "tool_call_budget": final_policy.tool_calls,
        "error_category": error_category,
        "answer": answer,
        "stores_prompt_or_answer": False,
    }
