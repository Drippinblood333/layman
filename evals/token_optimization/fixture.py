from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .cases import BenchmarkCase


TEST_MUTANTS = {
    "testing-01": (
        "def is_even(value):\n    return value > 0 and value % 2 == 0\n",
        "def is_even(value):\n    return value != 0 and value % 2 == 0\n",
        "def is_even(value):\n    return True\n",
    ),
    "testing-02": (
        "def first(values, default=None):\n    return default\n",
        "def first(values, default=None):\n    return values[0] if values else None\n",
        "def first(values, default=None):\n    return values[-1] if values else default\n",
    ),
    "testing-03": (
        "def divide(a, b):\n    return abs(a / b)\n",
        "def divide(a, b):\n    return 0 if b == 0 else a / b\n",
        "def divide(a, b):\n    return a + b\n",
    ),
    "testing-04": (
        "def normalize_space(text):\n    return text.strip()\n",
        "def normalize_space(text):\n    return ' '.join(text.split(' '))\n",
        "def normalize_space(text):\n    return text or ' '\n",
    ),
    "testing-05": (
        "def contains_all(values, required):\n    return any(item in values for item in required)\n",
        "def contains_all(values, required):\n    return set(required) == set(values)\n",
        "def contains_all(values, required):\n    return False\n",
    ),
}


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def prepare_workspace(case: BenchmarkCase, workspace: Path) -> None:
    if workspace.exists():
        raise FileExistsError(f"Benchmark workspace already exists: {workspace}")
    workspace.mkdir(parents=True)
    _write(workspace / ".gitignore", "__pycache__/\n*.py[cod]\n.pytest_cache/\n")
    _write(workspace / "README.md", "# Synthetic benchmark fixture\n")
    _write(workspace / "src" / "__init__.py", "")
    if case.source:
        _write(workspace / "src" / "target.py", case.source)
    for name, content in case.extra_files.items():
        _write(workspace / name, content)
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.email", "benchmark@local.invalid"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "Layman Benchmark"], cwd=workspace, check=True)
    subprocess.run(["git", "add", "-A"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=workspace, check=True)


def _changed_files(workspace: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "-uall"], cwd=workspace, capture_output=True, text=True, check=True,
    )
    changed = [line[3:].replace("\\", "/") for line in result.stdout.splitlines() if len(line) > 3]
    return sorted(
        path for path in changed
        if "__pycache__/" not in path and not path.endswith((".pyc", ".pyo")) and ".pytest_cache/" not in path
    )


def _validate_function(case: BenchmarkCase, workspace: Path) -> tuple[bool, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(workspace)
    result = subprocess.run(
        [sys.executable, "-c", case.hidden], cwd=workspace, env=environment,
        capture_output=True, text=True, timeout=30, check=False,
    )
    return result.returncode == 0, "hidden_function_checks" if result.returncode == 0 else "hidden_function_checks_failed"


def _validate_tests(case: BenchmarkCase, workspace: Path) -> tuple[bool, str]:
    test_path = workspace / "tests" / "test_target.py"
    if not test_path.exists():
        return False, "missing_test_file"

    command = [sys.executable, "-m", "pytest", "-q", "tests"]
    original_result = subprocess.run(
        command, cwd=workspace, capture_output=True, text=True, timeout=30, check=False,
    )
    if original_result.returncode != 0:
        return False, "tests_failed_on_reference"

    target = workspace / "src" / "target.py"
    original = target.read_text(encoding="utf-8")
    try:
        for mutant in TEST_MUTANTS[case.id]:
            target.write_text(mutant, encoding="utf-8")
            result = subprocess.run(
                command, cwd=workspace, capture_output=True, text=True, timeout=30, check=False,
            )
            if result.returncode == 0:
                return False, "mutation_survived"
    finally:
        target.write_text(original, encoding="utf-8")
    return True, "mutation_checks_passed"


def _validate_content(case: BenchmarkCase, workspace: Path) -> tuple[bool, str]:
    target = workspace / case.allowed_files[0]
    if not target.exists():
        return False, "missing_content_file"
    text = target.read_text(encoding="utf-8")
    passed = all(term.lower() in text.lower() for term in case.required)
    return passed, "required_content_present" if passed else "required_content_missing"


def validate_workspace(case: BenchmarkCase, workspace: Path, answer: str) -> dict[str, Any]:
    changed = _changed_files(workspace)
    allowed = {path.replace("\\", "/") for path in case.allowed_files}
    scope_ok = set(changed).issubset(allowed)
    if case.validator == "function":
        quality_ok, reason = _validate_function(case, workspace)
    elif case.validator == "tests":
        quality_ok, reason = _validate_tests(case, workspace)
    elif case.validator == "content":
        quality_ok, reason = _validate_content(case, workspace)
    else:
        lower = answer.lower()
        quality_ok = not changed and all(term.lower() in lower for term in case.required)
        reason = "read_only_plan_valid" if quality_ok else "read_only_plan_invalid"
    return {
        "passed": quality_ok and scope_ok,
        "quality_ok": quality_ok,
        "scope_ok": scope_ok,
        "changed_files": changed,
        "validation_reason": reason,
    }
