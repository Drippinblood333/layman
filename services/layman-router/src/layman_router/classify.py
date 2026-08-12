from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable

from .config import project_settings
from .models import RouterConfig, TaskFeatures, TaskType


INTENT_PATTERNS: list[tuple[TaskType, tuple[str, ...]]] = [
    (TaskType.DEBUGGING, (r"^(请|帮我|please\s+)?(debug|排查|修复|解决|fix)", r"(bug|traceback|报错|为什么失败|失败|内存泄漏|崩溃|异常).*(分析|原因|定位|排查|root cause|debug)")),
    (TaskType.SUMMARY, (r"^(请|帮我|please\s+)?(总结|摘要|提炼)", r"^(please\s+)?summari[sz]e\b")),
    (TaskType.REWRITE, (r"^(请|帮我|please\s+)?(改写|润色)", r"^(please\s+)?(rewrite|polish)\b")),
    (TaskType.TRANSLATION, (r"^(请|帮我|please\s+)?翻译", r"^(please\s+)?translate\b")),
    (TaskType.EXTRACTION, (r"^(请|帮我|please\s+)?(从.+)?提取", r"^(please\s+)?extract\b")),
    (TaskType.CLASSIFICATION, (r"^(请|帮我|please\s+)?(分类|打标签)", r"^(please\s+)?(classify|categorize)\b")),
    (TaskType.CODE_EXPLANATION, (r"^(请|帮我|please\s+)?解释.+(代码|函数|脚本|执行流程)", r"^(please\s+)?explain\b.+\b(code|function|script)\b")),
    (TaskType.ARCHITECTURE, (r"^(请|帮我)?(为.+)?(设计|评审).*(架构|方案|模块|边界|调用)", r"^(please\s+)?(design|review)\b.+\b(architecture|module|system)\b")),
    (TaskType.NORMAL_CODING, (r"^(请|帮我)?(实现|添加|增加|新增|创建|编写|开发|修改)", r"^(please\s+)?(implement|add|create|build|change)\b")),
]

KEYWORDS: list[tuple[TaskType, tuple[str, ...]]] = [
    (TaskType.SECURITY, ("security", "安全", "漏洞", "鉴权", "权限", "认证", "auth", "oauth", "payment", "支付", "secret")),
    (TaskType.ARCHITECTURE, ("architecture", "架构", "设计方案", "系统设计", "重构", "refactor")),
    (TaskType.DEBUGGING, ("traceback", "stack trace", "debug", "bug", "报错", "异常", "崩溃", "内存泄漏", "为什么失败")),
    (TaskType.MATH, ("数学", "证明", "方程", "calculus", "theorem", "derive", "求解")),
    (TaskType.TESTING, ("pytest", "unit test", "测试", "test case", "coverage")),
    (TaskType.DOCUMENTATION, ("readme", "文档", "documentation", "注释", "docstring")),
    (TaskType.CODE_EXPLANATION, ("解释代码", "执行流程", "code explanation", "explain this code", "代码含义")),
    (TaskType.SUMMARY, ("总结", "摘要", "summarize", "summary", "提炼")),
    (TaskType.TRANSLATION, ("翻译", "translate", "translation")),
    (TaskType.REWRITE, ("改写", "润色", "rewrite", "polish")),
    (TaskType.EXTRACTION, ("提取", "extract", "解析字段", "parse fields")),
    (TaskType.CLASSIFICATION, ("分类", "classify", "categorize", "打标签")),
    (TaskType.NORMAL_CODING, ("实现", "添加功能", "写代码", "coding", "implement", "组件")),
]

HIGH_RISK_TERMS = (
    "生产", "production", "支付", "payment", "安全", "security", "权限", "auth",
    "认证", "数据库迁移", "migration", "删除", "delete", "密钥", "secret",
)
MEDIUM_RISK_TERMS = ("部署", "deploy", "依赖", "dependency", "数据库", "database", "重构", "refactor")


def _contains_term(text: str, term: str) -> bool:
    if term.isascii() and term.replace(" ", "").isalnum():
        return bool(re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", text))
    return term in text


def _text_parts(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _text_parts(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in {"text", "content", "input", "instructions", "arguments"}:
                yield from _text_parts(item)
            elif key not in {"tools", "metadata"} and isinstance(item, (list, dict)):
                yield from _text_parts(item)


def extract_prompt_text(payload: dict[str, Any]) -> str:
    return "\n".join(part for key in ("instructions", "input") for part in _text_parts(payload.get(key)))


def classify_task(payload: dict[str, Any], config: RouterConfig) -> TaskFeatures:
    text = extract_prompt_text(payload)
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    project_id, _project, quality, budget = project_settings(config, metadata)
    tools = payload.get("tools") if isinstance(payload.get("tools"), list) else []
    has_code = "```" in text or bool(re.search(r"\b(def|class|function|import|const|let|SELECT|FROM)\b", text))

    task_type = next((candidate for candidate, patterns in INTENT_PATTERNS if any(re.search(pattern, normalized) for pattern in patterns)), TaskType.GENERAL)
    for candidate, terms in (KEYWORDS if task_type == TaskType.GENERAL else []):
        if any(_contains_term(normalized, term.lower()) for term in terms):
            task_type = candidate
            break

    prompt_chars = len(text)
    if prompt_chars > 12_000 or len(tools) >= 8 or (has_code and prompt_chars > 6_000):
        complexity = "high"
    elif prompt_chars > 2_000 or len(tools) >= 2 or has_code:
        complexity = "medium"
    else:
        complexity = "low"

    if any(_contains_term(normalized, term.lower()) for term in HIGH_RISK_TERMS):
        risk = "high"
    elif any(_contains_term(normalized, term.lower()) for term in MEDIUM_RISK_TERMS) or task_type in {TaskType.DEBUGGING, TaskType.ARCHITECTURE}:
        risk = "medium"
    else:
        risk = "low"

    digest_source = json.dumps({"instructions": payload.get("instructions"), "input": payload.get("input")}, ensure_ascii=False, sort_keys=True, default=str)
    prompt_hash = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
    return TaskFeatures(
        task_type=task_type,
        complexity=complexity,
        risk=risk,
        has_code=has_code,
        prompt_chars=prompt_chars,
        tool_count=len(tools),
        agentic=len(tools) >= 2,
        project_id=project_id,
        quality=quality,
        budget=budget,
        prompt_hash=prompt_hash,
    )
