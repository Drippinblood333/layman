"""Bounded offline clarification; never rewrite intent or infer permission."""
from __future__ import annotations

import re


def prompt_guidance(task: str) -> dict[str, object]:
    # Inspect only the leading request, not code, quotations or retrieved material.
    request = task.strip().lower()
    # Match courtesy endings only as part of a wholly unspecified request.
    # Do not strip them from concrete tasks, quotes or the original prompt.
    zh_end = r"\s*(?:吧)?(?:[，,\s]*谢谢)?[。！!\s]*"
    en_end = r"(?:,?\s+please)?[.!\s]*"
    broad = bool(re.fullmatch(
        rf"(?:请|帮我)?\s*(?:优化|完善|改进|重构)\s*(?:一下)?\s*(?:我的|这个|整个|全部)?\s*项目{zh_end}|"
        rf"(?:please\s+)?(?:optimize|improve|refactor)\s+(?:my|this|the whole|the entire)\s+project{en_end}",
        request,
    ))
    unspecified = bool(re.fullmatch(
        rf"(?:请|帮我)?\s*(?:优化|完善|改进|修复|重构)(?:一下)?{zh_end}|"
        rf"(?:please\s+)?(?:fix|improve|optimize|refactor)\s+(?:it|this){en_end}",
        request,
    ))
    questions = []
    if broad or unspecified:
        questions = [
            "你希望改善的具体结果是什么？例如安装步骤、某个报错或一个使用流程。",
            "怎样判断改善成功？如果仍需改进整个项目，先确认优先顺序，不缩减原始范围。",
        ]
    return {
        "method": "limited offline wording check; not semantic validation",
        "needs_clarification": bool(questions),
        "questions": questions,
        "original_intent_preserved": True,
        "rewritten": False,
        "model_calls": 0,
    }
