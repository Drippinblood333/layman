from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable

from .config import project_settings
from .models import RouterConfig, TaskFeatures, TaskType


INTENT_PATTERNS: list[tuple[TaskType, tuple[str, ...]]] = [
    (TaskType.DEBUGGING, (r"^(请|帮我|please\s+)?(debug|排查|定位)", r"(bug|traceback|报错|为什么失败|失败|内存泄漏|崩溃|异常).*(分析|原因|定位|排查|root cause|debug)")),
    (TaskType.SUMMARY, (r"^(请|帮我|please\s+)?(总结|摘要|提炼)", r"^(please\s+)?summari[sz]e\b")),
    (TaskType.REWRITE, (r"^(请|帮我|please\s+)?(改写|润色)", r"^(please\s+)?(rewrite|polish)\b")),
    (TaskType.TRANSLATION, (r"^(请|帮我|please\s+)?翻译", r"^(please\s+)?translate\b")),
    (TaskType.EXTRACTION, (r"^(请|帮我|please\s+)?(从.+)?提取", r"^(please\s+)?extract\b")),
    (TaskType.CLASSIFICATION, (r"^(请|帮我|please\s+)?(分类|打标签)", r"^(please\s+)?(classify|categorize)\b")),
    (TaskType.CODE_EXPLANATION, (r"^(请|帮我|please\s+)?解释.+(代码|函数|脚本|执行流程)", r"^(please\s+)?explain\b.+\b(code|function|script)\b")),
    (TaskType.ARCHITECTURE, (r"^(请|帮我)?(为.+)?(设计|评审).*(架构|方案|模块|边界|调用)", r"^(please\s+)?(design|review)\b.+\b(architecture|module|system)\b")),
    (TaskType.TESTING, (r"^(请|帮我)?(为.+)?(添加|增加|编写).*(测试|tests?)", r"^(please\s+)?(add|write|create)\b.+\btests?\b")),
    (TaskType.DOCUMENTATION, (r"^(请|帮我)?(更新|修改|添加).*(readme|文档|pyproject|config)", r"^(please\s+)?(update|change|edit|add)\b.+\b(readme|documentation|pyproject|config)\b")),
    (TaskType.NORMAL_CODING, (r"^(请|帮我)?(在.+)?(实现|添加|增加|新增|创建|编写|开发|修改|修复|解决)", r"^(please\s+)?(implement|add|create|build|change|fix)\b", r"^重构\s+\S+\.(py|js|ts|tsx|go|rs|java)\b")),
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

NEGATED_RISK_PATTERNS = (
    r"\bdo\s+not\s+(?:need\s+to\s+)?(?:delete|remove|access|use|change|modify|run|execute)\b[^.;\n]*",
    r"\bno\s+(?:production|payment|secret|database|auth(?:entication|orization)?)\b[^.;\n]*",
    r"(?:不要|不得|无需|不需要)[^。；\n]{0,24}(?:删除|生产|支付|密钥|数据库|权限|认证|执行|运行|修改)",
)

READ_ONLY_PATTERNS = (
    r"\bread[- ]only\b",
    r"\bdo\s+not\s+(?:run|execute|modify|change|delete|remove)\b",
    r"^(?:please\s+)?(?:review|explain|analy[sz]e)\b",
    r"^(?:请)?(?:只读评审|评审|解释|分析)\b",
    r"(?:只读|仅评审|不要|不得)[^。；\n]{0,20}(?:执行|运行|修改|删除|改动)",
)

DESTRUCTIVE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(?:sudo\s+)?rm\s+(?=[^\n;&|]*-[^\s;&|]*r)[^\n;&|]+", "recursive deletion"),
    (r"\bremove-item\b(?=[^\n;&|]*(?:-recurse\b|-r\b))[^\n;&|]+", "recursive deletion"),
    (r"\b(?:rmdir|rd)\s+/s\b|\bdel\s+/(?:s|q|f)", "recursive deletion"),
    (
        r"\bgit\s+reset\s+--hard\b|"
        r"\bgit\s+clean\b(?![^\n;&|]*(?:--dry-run\b|-[a-z]*n[a-z]*\b))"
        r"(?=[^\n;&|]*(?:--force\b|-[a-z]*f[a-z]*\b))[^\n;&|]*|"
        r"\bgit\s+restore\b|\bgit\s+checkout\s+(?:--\s+|\.\s*(?:$|[;&|]))|"
        r"\bgit\s+branch\s+-D\b",
        "destructive git history or worktree rewrite",
    ),
    (r"\bgit\s+push\b[^\n;&|]*(?:--force(?:-with-lease)?\b|-f\b)|\bforce\s+push\b", "forced remote history rewrite"),
    (r"\b(?:drop\s+(?:database|schema|table)|truncate\s+table)\b", "destructive database operation"),
    (r"\bdelete\s+from\s+[a-z0-9_.`\[\]-]+\s*(?:;|$)", "unbounded database deletion"),
    (r"\b(?:wipe|erase)\s+(?:the\s+)?(?:repository|repo|database|disk)\b", "destructive bulk deletion"),
    (r"\bremove\s+all\s+(?:user\s+)?accounts\b|删除(?:全部|所有)(?:用户|账户|账号|数据)", "destructive bulk account or data deletion"),
)


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


def _latest_task_text(payload: dict[str, Any]) -> str:
    value = payload.get("input")
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in reversed(value):
            if isinstance(item, dict) and item.get("role") == "user":
                text = "\n".join(_text_parts(item))
                if text.strip():
                    return text
        for item in reversed(value):
            if isinstance(item, str) and item.strip():
                return item
    return "\n".join(_text_parts(value)) or extract_prompt_text(payload)


def _active_call_text(payload: dict[str, Any]) -> str:
    calls: list[str] = []
    value = payload.get("input")
    for item in value if isinstance(value, list) else []:
        if isinstance(item, dict) and item.get("type") in {"function_call", "tool_call", "computer_call"}:
            calls.extend(_text_parts(item.get("arguments")))
    return "\n".join(calls)


def _without_negated_risk(text: str) -> str:
    for pattern in NEGATED_RISK_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return text


def destructive_intent(text: str) -> tuple[bool, str | None]:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    read_only = any(re.search(pattern, normalized, re.IGNORECASE) for pattern in READ_ONLY_PATTERNS)
    positive_text = _without_negated_risk(normalized)
    explicitly_executes = bool(re.search(r"\b(?:run|execute)\b|(?:并执行|然后执行|执行该|运行该)", positive_text))
    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, positive_text, re.IGNORECASE):
            if read_only and not explicitly_executes:
                return False, None
            return True, reason
    return False, None


def _agentic_intent(payload: dict[str, Any], task_text: str) -> bool:
    if _active_call_text(payload):
        return True
    normalized = re.sub(r"\s+", " ", task_text).lower()
    return bool(re.search(
        r"(交叉检查|对照).{0,20}(两个|多(?:个|处)|资料源|术语表)|"
        r"(两个|多(?:个|处)).{0,20}(来源|资料源|文件|工具)|"
        r"\b(?:use|call|invoke)\s+(?:the\s+)?(?:tools?|functions?)\b|"
        r"\b(?:cross-check|compare)\b.{0,24}\b(?:sources?|files?)\b",
        normalized,
    ))


def classify_task(payload: dict[str, Any], config: RouterConfig) -> TaskFeatures:
    text = extract_prompt_text(payload)
    task_text = _latest_task_text(payload)
    normalized = re.sub(r"\s+", " ", task_text).strip().lower()
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
    if prompt_chars > 12_000 or (has_code and prompt_chars > 6_000):
        complexity = "high"
    elif prompt_chars > 2_000 or has_code:
        complexity = "medium"
    else:
        complexity = "low"

    risk_source = "\n".join(filter(None, (task_text, _active_call_text(payload))))
    risk_text = _without_negated_risk(risk_source).lower()
    destructive, destructive_reason = destructive_intent(risk_source)
    if destructive or any(_contains_term(risk_text, term.lower()) for term in HIGH_RISK_TERMS):
        risk = "high"
    elif any(_contains_term(risk_text, term.lower()) for term in MEDIUM_RISK_TERMS) or task_type in {TaskType.DEBUGGING, TaskType.ARCHITECTURE}:
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
        agentic=_agentic_intent(payload, task_text),
        destructive=destructive,
        destructive_reason=destructive_reason,
        project_id=project_id,
        quality=quality,
        budget=budget,
        prompt_hash=prompt_hash,
    )
