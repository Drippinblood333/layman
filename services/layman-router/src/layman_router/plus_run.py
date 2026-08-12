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
    tool_output_tokens: int
    final_output_tokens: int
    compact_tokens: int
    verbosity: str


POLICIES = {
    RouteTier.FAST: TierExecutionPolicy(6, 10, 4_000, 2_000, 32_000, "low"),
    RouteTier.BALANCED: TierExecutionPolicy(10, 20, 8_000, 4_000, 48_000, "medium"),
    RouteTier.DEEP: TierExecutionPolicy(16, 32, 12_000, 8_000, 64_000, "medium"),
}


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


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
        "You are running under Layman's context-efficiency contract. Preserve the original request exactly. "
        f"{action} Search for named symbols, entrypoints, and tests before reading files. Start with at most "
        f"{policy.initial_files} unique files. Expand once, only with a concrete reason, up to "
        f"{policy.expanded_files}; otherwise stop and report missing context. Do not scan the whole repository, "
        "repeat file contents, or print full test logs. Reuse evidence already obtained. Keep the final response "
        f"under roughly {policy.final_output_tokens} tokens and include only outcome, verification, risks, and next step. "
        "Identify the user-visible done condition before editing, follow existing project conventions, and do not ask "
        "the user to choose technical details that repository evidence answers safely. Explain the result plainly. "
        f"Selected workflow: {workflow}. Selected route: {tier.value}."
    )


def _candidate_tiers(selected: RouteTier) -> list[RouteTier]:
    if selected == RouteTier.FAST:
        return [RouteTier.FAST, RouteTier.BALANCED, RouteTier.DEEP]
    if selected == RouteTier.BALANCED:
        return [RouteTier.BALANCED, RouteTier.DEEP]
    return [RouteTier.DEEP]


def plus_task_plan(task: str, *, config: Any | None = None) -> dict[str, Any]:
    if not task.strip():
        raise ValueError("Task from stdin must not be empty")
    config = config or load_config()
    payload = {"model": "auto", "input": task}
    features = classify_task(payload, config)
    decision = decide_route(features, config)
    policy = POLICIES[decision.route_tier]
    return {
        "route_tier": decision.route_tier.value,
        "model": decision.selected_model,
        "effort": decision.reasoning_effort,
        "route_reason": decision.route_reason,
        "task_type": features.task_type.value,
        "workflow": select_workflow(features.task_type, features.risk),
        "risk": features.risk,
        "sandbox": "read-only" if features.risk == "high" else "workspace-write",
        "initial_file_budget": policy.initial_files,
        "expanded_file_budget": policy.expanded_files,
        "tool_output_token_limit": policy.tool_output_tokens,
        "final_output_token_budget": policy.final_output_tokens,
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
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    config = load_config()
    preview = plus_task_plan(task, config=config)
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
    executable = find_codex(codex_path)
    login = codex_login_status(executable, runner=runner)
    if not login["available"] or not login["chatgpt_login"]:
        raise RuntimeError("Codex must be logged in with ChatGPT; refusing API-key billing")

    selected = RouteTier(preview["route_tier"])
    started = time.perf_counter()
    attempts: list[dict[str, str]] = []
    answer = ""
    usage: dict[str, int] = {}
    metrics = {"tool_calls": 0, "unique_files_read": 0, "compactions": 0}
    status = "failed"
    error_category: str | None = None
    final_tier = selected

    for tier in _candidate_tiers(selected):
        spec = config.tiers[tier]
        policy = POLICIES[tier]
        read_only = preview["risk"] == "high"
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
            except subprocess.TimeoutExpired:
                error_category = "timeout"
                attempts.append({"tier": tier.value, "model": spec.model, "status": error_category})
                final_tier = tier
                break
            answer = last_message.read_text(encoding="utf-8") if last_message.exists() else ""
            usage = _usage_from_events(result.stdout)
            metrics = event_metrics(result.stdout)
            error_category = None if result.returncode == 0 else _safe_error(result.stderr, result.returncode)
            attempts.append({"tier": tier.value, "model": spec.model, "status": error_category or "completed"})
            final_tier = tier
            if result.returncode == 0:
                status = "completed"
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
        "latency_ms": round((time.perf_counter() - started) * 1_000),
        **metrics,
        "file_budget": {"initial": final_policy.initial_files, "expanded": final_policy.expanded_files},
        "error_category": error_category,
        "answer": answer,
        "stores_prompt_or_answer": False,
    }
