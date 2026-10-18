from __future__ import annotations

import re

from .models import TaskType

WORKFLOWS = {
    TaskType.DEBUGGING: "reproduce-fix-verify",
    TaskType.TESTING: "discover-test-gaps-verify",
    TaskType.ARCHITECTURE: "understand-design-slice",
    TaskType.SECURITY: "read-only-risk-review",
    TaskType.DOCUMENTATION: "inspect-update-check-links",
    TaskType.NORMAL_CODING: "understand-implement-verify",
}


def _requests_release(task: str) -> bool:
    # Narrow intent filtering only, never authorization or task rewriting.
    # Future approval boilerplate is not a current release/check request.
    normalized = task.lower()
    for pattern in (
        r"(?:公开|正式)?(?:发布|发版|上线)时\s*[,，]?\s*(?:我|我们)(?:均|都)?(?:会)?(?:批准|同意|授权)",
        (
            r"\b(?:if|when)\s+(?:(?:i|we|you)\s+)?(?:release|publish|ship)\b\s*[,，]?\s*"
            r"(?:i|we)\s+(?:will\s+)?(?:approve|authorize|consent)\b"
        ),
    ):
        normalized = re.sub(pattern, " ", normalized)
    return bool(re.search(r"\b(?:release|publish|ship)\b", normalized)) or any(
        term in normalized for term in ("上线", "发布", "发版")
    )


def select_workflow(task_type: TaskType, risk: str, *, project_stage: str | None = None, task: str = "") -> str:
    if risk == "high":
        return "read-only-risk-review"
    if project_stage in {"idea", "discovery"} and task_type in {TaskType.GENERAL, TaskType.ARCHITECTURE}:
        return "idea-to-smallest-usable-version"
    if project_stage == "release_candidate" and _requests_release(task):
        return "release-gate"
    return WORKFLOWS.get(task_type, "scope-execute-verify")
