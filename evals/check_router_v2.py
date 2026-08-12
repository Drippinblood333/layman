#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "services" / "layman-router"
PLUGIN = ROOT / "plugins" / "layman"
sys.path.insert(0, str(ROUTER / "src"))

from layman_router.classify import classify_task
from layman_router.config import load_config
from layman_router.routing import decide_route


def main() -> int:
    failures = []
    required = [
        ROUTER / "pyproject.toml",
        ROUTER / "src" / "layman_router" / "app.py",
        ROUTER / "config" / "projects.yaml",
        PLUGIN / ".codex-plugin" / "plugin.json",
        PLUGIN / "skills" / "layman" / "SKILL.md",
        PLUGIN / "skills" / "layman-router" / "SKILL.md",
        ROOT / "evals" / "router-v2" / "cases.jsonl",
    ]
    for path in required:
        if not path.exists():
            failures.append(f"missing {path.relative_to(ROOT)}")

    cases_path = ROOT / "evals" / "router-v2" / "cases.jsonl"
    if cases_path.exists():
        cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line]
        categories = Counter(item["category"] for item in cases)
        if len(cases) != 300:
            failures.append(f"expected 300 eval cases, got {len(cases)}")
        if set(categories.values()) != {50} or len(categories) != 6:
            failures.append(f"eval category counts invalid: {dict(categories)}")
        config = load_config()
        for case in cases:
            payload = case.get("request") or {"model": "auto", "input": case["input"]}
            features = classify_task(payload, config)
            decision = decide_route(features, config, payload.get("metadata"))
            if (features.task_type.value, features.risk, decision.route_tier.value) != (
                case["expected_task_type"], case["expected_risk"], case["expected_tier"]
            ):
                failures.append(f"routing mismatch {case['id']}: {features.task_type.value}/{features.risk}/{decision.route_tier.value}")
            if features.risk == "high" and decision.route_tier.value != "deep":
                failures.append(f"high-risk under-route {case['id']}")

    for base in (ROUTER, PLUGIN):
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".md", ".json", ".yaml", ".toml"}:
                text = path.read_text(encoding="utf-8")
                if "[TODO" in text or "placeholder" in text.lower():
                    failures.append(f"placeholder found in {path.relative_to(ROOT)}")

    checksum = (ROOT / "dist" / "layman-skill-v1.zip.sha256").read_text(encoding="utf-8").split()[0].upper()
    actual = hashlib.sha256((ROOT / "dist" / "layman-skill-v1.zip").read_bytes()).hexdigest().upper()
    if checksum != actual:
        failures.append("v1 release ZIP checksum changed")

    if failures:
        print("Layman 1.0 checks failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Layman 1.0 structure, unified plugin, 300-case eval set, privacy checks, and legacy v1 artifact checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
