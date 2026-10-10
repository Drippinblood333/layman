"""Owner-approved eight-execution trial; review answers never enter telemetry."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from layman_router.plus_eval import PlusEvalArm, run_plus_eval


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--codex-path", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    private = root / "build" / "private-plus-review-2026-10-10"
    private.mkdir(parents=True, exist_ok=True)
    cases = [
        {"id": "review-summary", "category": "summary", "input": "请用不超过三条总结这段虚构记录，保留限制：校园借阅工具新增离线查询；离线时不能办理借还；联网后才同步记录。首版仅邀请内部试用，尚未公开发布。"},
        {"id": "review-rewrite", "category": "rewrite", "input": "请合并下面两条虚构通知，保持事实，不超过100字：周日下午二层自助打印机维护；一层人工打印窗口正常开放，维护结束时间尚未确定。", "request": {"model": "auto", "input": "请合并下面两条虚构通知，保持事实，不超过100字：周日下午二层自助打印机维护；一层人工打印窗口正常开放，维护结束时间尚未确定。", "tools": [{"type": "function", "name": "merge_notice"}, {"type": "function", "name": "read_notice"}]}},
        {"id": "review-debugging", "category": "debugging", "input": "这个bug请分析原因，给出最小修复和回归用例：Python函数 def add_item(item, items=[]): items.append(item); return items。不同调用者希望每次不传items时得到独立列表，显式传入列表时仍修改该列表。"},
        {"id": "review-extraction", "category": "extraction", "input": "从这条虚构记录提取id、status、owner，严格返回JSON，不补充缺失信息：id=R-204; status=awaiting_review; owner字段未提供。缺失字段用null。"},
    ]
    cases_path = private / "cases.jsonl"
    rendered = "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases)
    if cases_path.exists():
        if cases_path.read_text(encoding="utf-8") != rendered:
            raise RuntimeError("Private corpus changed; refuse to replace approved experiment")
    else:
        with cases_path.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
    labels = {
        f"{case['id']}:{arm}": f"R{index + 1:02d}-{letter}"
        for index, case in enumerate(cases)
        for arm, letter in (("auto", "A" if index % 2 == 0 else "B"),
                            ("always_deep", "B" if index % 2 == 0 else "A"))
    }

    def save_review(arm: PlusEvalArm, answer: str) -> None:
        target = private / f"{labels[arm.key]}.txt"
        with target.open("x", encoding="utf-8") as stream:
            stream.write(answer)

    result = run_plus_eval(
        cases_path=cases_path, output=private / "results.jsonl", workspace=private / "workspace",
        codex_path=args.codex_path, execute=args.run, max_calls=8, total_call_cap=8,
        review_sink=save_review,
    )
    if args.run:
        review = ["# 本地人工评审\n", "请先评分，再查看结果日志中的模型信息。A/B仅隐藏展示标签，不代表随机执行顺序。\n",
                  "每份回答：正确性0–2、要求遵循0–2、清晰简洁0–2；记录事实错误。未评分不算通过。此4对试验不替代发布验收。\n"]
        for index, case in enumerate(cases):
            review.extend([f"\n## R{index + 1:02d}\n", case["input"] + "\n"])
            for letter in ("A", "B"):
                target = private / f"R{index + 1:02d}-{letter}.txt"
                review.extend([f"\n### 回答 {letter}\n", target.read_text(encoding="utf-8") if target.exists() else "未完成",
                               "\n\n评分：正确性 __ /2；要求遵循 __ /2；清晰简洁 __ /2；备注：__\n"])
        with (private / "REVIEW.md").open("w", encoding="utf-8") as stream:
            stream.write("\n".join(review))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
