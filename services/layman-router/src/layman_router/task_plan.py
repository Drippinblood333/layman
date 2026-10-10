from __future__ import annotations

from pathlib import Path
from typing import Any

from .classify import classify_task
from .config import load_config
from .plus_run import plus_task_plan
from .project_status import inspect_project
from .workflow import select_workflow


def create_task_plan(task: str, workspace: str | Path) -> dict[str, Any]:
    if not task.strip():
        raise ValueError("Task must not be empty")
    root = Path(workspace).expanduser().resolve()
    project = inspect_project(root)
    config = load_config()
    features = classify_task({"model": "auto", "input": task}, config)
    route = plus_task_plan(task, config=config)

    workflow = select_workflow(features.task_type, features.risk, project_stage=project["stage"], task=task)
    guidance = route["prompt_guidance"]

    modules = ["context", f"workflow:{workflow}", "routing", "output"]
    if features.risk != "low":
        modules.append("safety")
    if features.task_type.value not in {
        "summary",
        "rewrite",
        "translation",
        "classification",
        "extraction",
    }:
        modules.append("verification")

    plan_first = guidance["needs_clarification"] or features.risk == "high" or workflow in {"idea-to-smallest-usable-version", "read-only-risk-review"}
    acceptance = [
        "The requested user-visible outcome is present.",
        "The smallest relevant automated or manual verification succeeds.",
        "No unrelated files or behaviors are changed.",
    ]
    if features.risk == "high":
        acceptance.append("Implementation starts only after the read-only risk review is accepted.")

    return {
        "workspace": str(root),
        "project_stage": project["stage"],
        "task_type": features.task_type.value,
        "risk": features.risk,
        "complexity": features.complexity,
        "workflow": workflow,
        "selected_modules": modules,
        "execution": "plan-first" if plan_first else "execute-and-verify",
        "route": route,
        "acceptance_criteria": acceptance,
        "prompt_guidance": guidance,
        "stop_conditions": [
            "Required context exceeds the selected file budget.",
            "The task requires an unrelated broad refactor or destructive operation.",
            "Verification contradicts the claimed outcome.",
        ],
        "next_steps": [
            "Answer the clarification questions, then resubmit the original request with those details; no execution has started.",
        ] if guidance["needs_clarification"] else project["next_steps"] if workflow == "release-gate" else [
            "Inspect only the code and context needed for the requested task.",
            "Review the scoped plan before implementation." if plan_first else "Make the smallest complete change for the requested outcome.",
            "Run verification proportionate to this change and report any remaining risk.",
        ],
        "task_chars": len(task),
        "stores_task_or_code": False,
    }
