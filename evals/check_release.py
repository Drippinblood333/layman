#!/usr/bin/env python3
"""Release checks for Layman Skill v1."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "layman-skill"
SKILL_MD = SKILL_DIR / "SKILL.md"
OPENAI_YAML = SKILL_DIR / "agents" / "openai.yaml"

REQUIRED_REFERENCES = [
    "prompt-scorecard.md",
    "task-patterns.md",
    "project-stages.md",
    "bad-prompts.md",
    "release-checklist.md",
]

REQUIRED_EXAMPLES = [
    "bad-to-good-prompts.md",
    "idea-to-roadmap.md",
    "project-handoff.md",
]

REQUIRED_OUTPUT_LABELS = [
    "原始需求 / Original request",
    "风险判断 / Risk",
    "主要问题 / Issues",
    "建议拆分 / Breakdown",
    "推荐先执行的任务 / First task",
    "可复制给 Codex 的 prompt / Copyable prompt",
    "验收标准 / Acceptance criteria",
    "停止条件 / Stop conditions",
    "不建议现在做的事 / Not now",
    "下一步 / Next step",
]

REQUIRED_SCENARIOS = [
    "Idea to MVP",
    "Prompt audit",
    "Safe task generation",
    "New project handoff",
    "Pre-release check",
]

EXPECTED_EVAL_SCENARIOS = {
    "idea_to_mvp",
    "prompt_audit",
    "safe_task_generation",
    "new_project_handoff",
    "pre_release_check",
}

PLACEHOLDER_PATTERNS = [
    "TODO",
    "[TODO",
    "placeholder",
    "Replace with",
    "Complete and informative",
]


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_exists(path: Path, failures: list[str]) -> None:
    if not path.exists():
        fail(f"Missing required path: {path.relative_to(ROOT)}", failures)


def check_skill_metadata(failures: list[str]) -> None:
    check_exists(SKILL_MD, failures)
    if not SKILL_MD.exists():
        return

    content = read_text(SKILL_MD)
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        fail("SKILL.md frontmatter is missing or malformed.", failures)
        return

    frontmatter = match.group(1)
    keys = {
        line.split(":", 1)[0].strip()
        for line in frontmatter.splitlines()
        if ":" in line and not line.startswith(" ")
    }
    if keys != {"name", "description"}:
        fail(f"SKILL.md frontmatter keys must be name and description only; got {sorted(keys)}.", failures)

    if "name: layman-skill" not in frontmatter:
        fail("SKILL.md frontmatter must declare name: layman-skill.", failures)
    if "Version: v1" not in content:
        fail("SKILL.md body must include Version: v1.", failures)


def check_openai_yaml(failures: list[str]) -> None:
    check_exists(OPENAI_YAML, failures)
    if not OPENAI_YAML.exists():
        return

    content = read_text(OPENAI_YAML)
    required = [
        'display_name: "Layman Skill"',
        'short_description: "把模糊想法和坏提示词改成安全可验收 AI Coding 任务"',
        'default_prompt: "Use $layman-skill',
    ]
    for marker in required:
        if marker not in content:
            fail(f"agents/openai.yaml missing marker: {marker}", failures)
    forbidden = ["dependencies:", "icon_small:", "icon_large:", "brand_color:"]
    for marker in forbidden:
        if marker in content:
            fail(f"agents/openai.yaml should not include v1 optional field: {marker}", failures)


def check_references_and_body(failures: list[str]) -> None:
    content = read_text(SKILL_MD) if SKILL_MD.exists() else ""
    for filename in REQUIRED_REFERENCES:
        ref_path = SKILL_DIR / "references" / filename
        check_exists(ref_path, failures)
        if filename not in content:
            fail(f"SKILL.md does not mention reference file: {filename}", failures)

    for label in REQUIRED_OUTPUT_LABELS:
        if label not in content:
            fail(f"SKILL.md missing required output label: {label}", failures)

    for scenario in REQUIRED_SCENARIOS:
        if scenario not in content:
            fail(f"SKILL.md missing scenario: {scenario}", failures)

    forbidden_skill_docs = ["README.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md", "QUICK_REFERENCE.md"]
    for filename in forbidden_skill_docs:
        if (SKILL_DIR / filename).exists():
            fail(f"Do not place auxiliary docs inside skill folder: {filename}", failures)


def check_examples_and_evals(failures: list[str]) -> None:
    for filename in REQUIRED_EXAMPLES:
        check_exists(ROOT / "examples" / filename, failures)

    prompts_path = ROOT / "evals" / "prompts.json"
    rubric_path = ROOT / "evals" / "expected-output-rubric.md"
    check_exists(prompts_path, failures)
    check_exists(rubric_path, failures)
    if not prompts_path.exists():
        return

    try:
        prompts = json.loads(read_text(prompts_path))
    except json.JSONDecodeError as exc:
        fail(f"evals/prompts.json is invalid JSON: {exc}", failures)
        return

    if len(prompts) != 5:
        fail(f"Expected 5 eval prompts, got {len(prompts)}.", failures)

    scenarios = {item.get("scenario") for item in prompts}
    if scenarios != EXPECTED_EVAL_SCENARIOS:
        fail(f"Eval scenarios mismatch: {sorted(scenarios)}.", failures)

    for item in prompts:
        for key in ["id", "scenario", "input", "must_include", "must_not_include"]:
            if key not in item:
                fail(f"Eval prompt missing key {key}: {item}", failures)


def check_placeholders(failures: list[str]) -> None:
    targets = [SKILL_DIR, ROOT / "examples", ROOT / "evals" / "prompts.json", ROOT / "evals" / "expected-output-rubric.md"]
    paths: list[Path] = []
    for target in targets:
        paths.extend(target.rglob("*") if target.is_dir() else [target])
    for path in paths:
        if not path.is_file():
            continue
        try:
            content = read_text(path)
        except UnicodeDecodeError:
            continue
        for marker in PLACEHOLDER_PATTERNS:
            if marker in content:
                fail(f"Placeholder marker {marker!r} found in {path.relative_to(ROOT)}.", failures)


def main() -> int:
    failures: list[str] = []
    check_skill_metadata(failures)
    check_openai_yaml(failures)
    check_references_and_body(failures)
    check_examples_and_evals(failures)
    check_placeholders(failures)

    if failures:
        print("Layman Skill v1 release checks failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Layman Skill v1 release checks passed.")
    print("- Skill metadata, UI metadata, references, examples, evals, and placeholders checked.")
    print("- Five MVP scenarios and required output labels are present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
