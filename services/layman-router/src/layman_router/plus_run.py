from __future__ import annotations

import json
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .classify import classify_task
from .config import load_config
from .execution_control import CancellationToken, USAGE_KEYS, run_streaming_process
from .models import RouteTier, TaskType
from .plus_eval import _safe_error, _usage_from_events, codex_login_status, event_metrics, find_codex, subscription_environment
from .project_status import inspect_project
from .routing import decide_route
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
    aliases = {"input_tokens", "cached_input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens"}

    def visit(value: Any) -> bool:
        if isinstance(value, dict):
            return any(key in aliases and isinstance(child, int) for key, child in value.items()) or any(
                visit(child) for child in value.values()
            )
        if isinstance(value, list):
            return any(visit(child) for child in value)
        return False

    for line in stdout.splitlines():
        try:
            if visit(json.loads(line)):
                return True
        except json.JSONDecodeError:
            continue
    return False


def _text_output(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def _execution_contract(tier: RouteTier, policy: TierExecutionPolicy, *, read_only: bool, workflow: str) -> str:
    action = (
        "Analyze only; do not modify files."
        if read_only
        else (
            "The user has authorized implementation. When the request asks to fix, create, change, or implement, "
            "you must edit the workspace and run the smallest relevant verification in this turn. Do not stop at "
            "analysis, offer a patch as a suggestion, or ask whether to proceed. Implement only the requested change."
        )
    )
    return (
        f"Layman route={tier.value}; workflow={workflow}. Preserve the request. {action} "
        "Search named symbols and tests first; read only evidence needed for the done condition. "
        f"The file limits are ceilings, not targets: {policy.initial_files} initially and {policy.expanded_files} "
        f"only after a concrete evidence gap; do not exceed {policy.tool_calls} tool calls. "
        "Reuse prior evidence; avoid broad scans, repeated contents, and full logs. "
        f"Target about {policy.final_output_token_target} final-answer tokens: outcome, reported verification evidence, "
        "residual risk, and next step. This is a concision target, not a truncation boundary."
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
    features = classify_task(payload, config)
    decision = decide_route(features, config)
    policy = POLICIES[decision.route_tier]
    destructive_blocked = features.destructive and not allow_destructive
    read_only = features.risk == "high" and not (features.destructive and allow_destructive)
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
        "execution_allowed": not destructive_blocked,
        "sandbox": "read-only" if read_only else "workspace-write",
        "initial_file_budget": policy.initial_files,
        "expanded_file_budget": policy.expanded_files,
        "tool_call_budget": policy.tool_calls,
        "tool_output_token_limit": policy.tool_output_tokens,
        "final_output_token_target": policy.final_output_token_target,
        "compact_token_limit": policy.compact_tokens,
        "stores_prompt_or_answer": False,
    }


def run_plus_task(
    task: str,
    *,
    cwd: Path,
    codex_path: str | None = None,
    timeout_seconds: int = 1_800,
    execute: bool = True,
    allow_destructive: bool = False,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    cancel_token: CancellationToken | None = None,
) -> dict[str, Any]:
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
            "error_category": "destructive_authorization_required",
            "answer": (
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
    aggregate_metrics = {"tool_calls": 0, "unique_files_read": 0, "compactions": 0}
    status = "failed"
    error_category: str | None = None
    final_tier = selected

    for tier in _candidate_tiers(selected):
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
