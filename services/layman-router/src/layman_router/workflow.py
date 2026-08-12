from __future__ import annotations

from .models import TaskType


WORKFLOWS = {
    TaskType.DEBUGGING: "reproduce-fix-verify",
    TaskType.TESTING: "discover-test-gaps-verify",
    TaskType.ARCHITECTURE: "understand-design-slice",
    TaskType.SECURITY: "read-only-risk-review",
    TaskType.DOCUMENTATION: "inspect-update-check-links",
    TaskType.NORMAL_CODING: "understand-implement-verify",
}


def select_workflow(task_type: TaskType, risk: str, *, project_stage: str | None = None, task: str = "") -> str:
    normalized = task.lower()
    release_request = any(term in normalized for term in ("release", "publish", "ship", "上线", "发布", "发版"))
    if risk == "high":
        return "read-only-risk-review"
    if project_stage in {"idea", "discovery"} and task_type in {TaskType.GENERAL, TaskType.ARCHITECTURE}:
        return "idea-to-smallest-usable-version"
    if project_stage == "release_candidate" and release_request:
        return "release-gate"
    return WORKFLOWS.get(task_type, "scope-execute-verify")
