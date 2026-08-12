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

    plan_first = features.risk == "high" or workflow in {"idea-to-smallest-usable-version", "read-only-risk-review"}
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
        "stop_conditions": [
            "Required context exceeds the selected file budget.",
            "The task requires an unrelated broad refactor or destructive operation.",
            "Verification contradicts the claimed outcome.",
        ],
        "next_steps": project["next_steps"],
        "task_chars": len(task),
        "stores_task_or_code": False,
    }
