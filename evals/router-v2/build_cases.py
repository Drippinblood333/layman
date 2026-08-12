#!/usr/bin/env python3
"""Generate 300 varied routing cases, including adversarial and boundary prompts."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DOMAINS = ["学生工具", "订单服务", "数据看板", "内容平台", "内部 API"]
TOOLS_1 = [{"type": "function", "name": "read_file", "description": "Read one file", "parameters": {"type": "object"}}]
TOOLS_2 = TOOLS_1 + [{"type": "function", "name": "search", "description": "Search files", "parameters": {"type": "object"}}]
LONG_SUFFIX = " 背景资料" * 2700


SCENARIOS = {
    "summary": [
        ("请总结{domain}的变更说明，保留结论。", "summary", "fast", "low", {}),
        ("Summarize the {domain} release note in three bullets.", "summary", "fast", "low", {}),
        ("请总结{domain}的上一轮讨论。", "summary", "fast", "low", {"previous_response_id": "resp_previous"}),
        ("请总结{domain}文件的主要内容。", "summary", "fast", "low", {"tools": TOOLS_1}),
        ("请总结{domain}并交叉检查两个资料源。", "summary", "balanced", "low", {"tools": TOOLS_2}),
        ("请总结{domain}的长篇材料。{long}", "summary", "balanced", "low", {}),
        ("请总结{domain}的生产安全漏洞报告。", "summary", "deep", "high", {}),
        ("请总结{domain}的支付认证事故。", "summary", "deep", "high", {"metadata": {"layman_route": "fast"}}),
        ("请总结{domain}的公开介绍。", "summary", "fast", "low", {"metadata": {"layman_budget": "low"}}),
        ("请总结{domain}的数据库部署方案。", "summary", "deep", "medium", {"metadata": {"layman_quality": "production"}}),
    ],
    "rewrite": [
        ("请润色{domain}的欢迎文案，保持原意。", "rewrite", "fast", "low", {}),
        ("Rewrite the {domain} onboarding copy in a warmer tone.", "rewrite", "fast", "low", {}),
        ("请改写{domain}这段普通公告。", "rewrite", "fast", "low", {"previous_response_id": "resp_previous"}),
        ("请润色{domain}文件里的标题。", "rewrite", "fast", "low", {"tools": TOOLS_1}),
        ("请改写{domain}并对照两个术语表。", "rewrite", "balanced", "low", {"tools": TOOLS_2}),
        ("请润色{domain}的长文。{long}", "rewrite", "balanced", "low", {}),
        ("请改写{domain}的生产环境删除警告。", "rewrite", "deep", "high", {}),
        ("请润色{domain}的 OAuth 密钥轮换通知。", "rewrite", "deep", "high", {}),
        ("请改写{domain}的短按钮文案。", "rewrite", "fast", "low", {"metadata": {"layman_budget": "low"}}),
        ("请润色{domain}的数据库迁移说明。", "rewrite", "deep", "high", {"metadata": {"layman_route": "fast"}}),
    ],
    "code_explanation": [
        ("解释{domain}这个 Python 函数的执行流程。", "code_explanation", "balanced", "low", {}),
        ("Explain this code function used by {domain}.", "code_explanation", "balanced", "low", {}),
        ("请解释{domain}中的函数，不要修改。", "code_explanation", "balanced", "low", {"previous_response_id": "resp_previous"}),
        ("请解释{domain}文件里的函数。", "code_explanation", "balanced", "low", {"tools": TOOLS_1}),
        ("请解释{domain}两处函数的调用关系。", "code_explanation", "balanced", "low", {"tools": TOOLS_2}),
        ("请解释{domain}的长代码。{long}", "code_explanation", "balanced", "low", {}),
        ("请解释{domain}的支付鉴权代码。", "code_explanation", "deep", "high", {}),
        ("请解释{domain}的生产删除脚本。", "code_explanation", "deep", "high", {"metadata": {"layman_route": "fast"}}),
        ("请解释{domain}这个简单 getter 函数。", "code_explanation", "fast", "low", {"metadata": {"layman_budget": "low"}}),
        ("请解释{domain}的数据库访问函数。", "code_explanation", "deep", "medium", {"metadata": {"layman_quality": "production"}}),
    ],
    "debugging": [
        ("{domain}出现 bug，请分析报错原因。", "debugging", "deep", "medium", {}),
        ("Debug the traceback from {domain}; identify root cause.", "debugging", "deep", "medium", {}),
        ("{domain}为什么失败？只诊断，不改代码。", "debugging", "deep", "medium", {}),
        ("{domain}发生内存泄漏，请定位原因。", "debugging", "deep", "medium", {"tools": TOOLS_1}),
        ("{domain}间歇性崩溃，请结合日志和代码分析。", "debugging", "deep", "medium", {"tools": TOOLS_2}),
        ("{domain}出现长 traceback。{long}", "debugging", "deep", "medium", {}),
        ("{domain}生产支付服务报错，请排查。", "debugging", "deep", "high", {}),
        ("{domain}认证失败，请 debug。", "debugging", "deep", "high", {"metadata": {"layman_route": "fast"}}),
        ("{domain}的小测试为什么失败？", "debugging", "deep", "medium", {"metadata": {"layman_budget": "low"}}),
        ("{domain}数据库异常，需要生产级诊断。", "debugging", "deep", "high", {"metadata": {"layman_quality": "production"}}),
    ],
    "architecture": [
        ("为{domain}评审架构设计方案。", "architecture", "deep", "medium", {}),
        ("Review the architecture of {domain} and explain tradeoffs.", "architecture", "deep", "medium", {}),
        ("为{domain}制定重构边界。", "architecture", "deep", "medium", {}),
        ("评审{domain}架构并读取现有说明。", "architecture", "deep", "medium", {"tools": TOOLS_1}),
        ("设计{domain}跨模块调用方案。", "architecture", "deep", "medium", {"tools": TOOLS_2}),
        ("评审{domain}的大型系统设计。{long}", "architecture", "deep", "medium", {}),
        ("设计{domain}支付认证架构。", "architecture", "deep", "high", {}),
        ("设计{domain}生产数据库迁移方案。", "architecture", "deep", "high", {"metadata": {"layman_route": "fast"}}),
        ("为{domain}设计一个最小模块边界。", "architecture", "deep", "medium", {"metadata": {"layman_budget": "low"}}),
        ("评审{domain}生产架构。", "architecture", "deep", "high", {"metadata": {"layman_quality": "production"}}),
    ],
    "extraction": [
        ("从{domain}文本中提取名称、日期和状态并返回 JSON。", "extraction", "fast", "low", {}),
        ("Extract name, date, and state from the {domain} note.", "extraction", "fast", "low", {}),
        ("请从{domain}上一轮结果提取字段。", "extraction", "fast", "low", {"previous_response_id": "resp_previous"}),
        ("请从{domain}文件提取三个字段。", "extraction", "fast", "low", {"tools": TOOLS_1}),
        ("请从{domain}两个来源提取并去重。", "extraction", "balanced", "low", {"tools": TOOLS_2}),
        ("请从{domain}长材料提取字段。{long}", "extraction", "balanced", "low", {}),
        ("请从{domain}生产安全报告提取漏洞等级。", "extraction", "deep", "high", {}),
        ("请从{domain}支付认证记录提取密钥状态。", "extraction", "deep", "high", {"metadata": {"layman_route": "fast"}}),
        ("请从{domain}短句提取名称。", "extraction", "fast", "low", {"metadata": {"layman_budget": "low"}}),
        ("请从{domain}数据库部署记录提取版本。", "extraction", "deep", "medium", {"metadata": {"layman_quality": "production"}}),
    ],
}


def main() -> None:
    cases = []
    for category, scenarios in SCENARIOS.items():
        for domain_index, domain in enumerate(DOMAINS):
            for scenario_index, (template, task_type, tier, risk, extra) in enumerate(scenarios):
                index = domain_index * len(scenarios) + scenario_index + 1
                request = {"model": "auto", "input": template.format(domain=domain, long=LONG_SUFFIX)}
                request.update(extra)
                cases.append({
                    "id": f"{category}-{index:03d}", "category": category,
                    "input": request["input"], "request": request,
                    "expected_task_type": task_type, "expected_tier": tier, "expected_risk": risk,
                    "human_score_auto": None, "human_score_deep": None,
                })
    target = ROOT / "cases.jsonl"
    target.write_text("".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases), encoding="utf-8")
    print(f"wrote {len(cases)} varied cases to {target}")


if __name__ == "__main__":
    main()
