from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

IGNORED_TOP_LEVEL = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "release",
    "target",
}

MANIFEST_NAMES = {
    "Cargo.toml",
    "Gemfile",
    "go.mod",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "requirements.txt",
}
SOURCE_NAMES = {"app", "apps", "cmd", "lib", "packages", "services", "src"}
TEST_NAMES = {"e2e", "spec", "specs", "test", "tests"}
LOCK_NAMES = {
    "Cargo.lock",
    "Gemfile.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "requirements.lock",
    "uv.lock",
    "yarn.lock",
}


def _relative_markers(root: Path, names: set[str], *, parents: list[Path], directories: bool | None = None) -> list[str]:
    matches: set[Path] = set()
    for name in names:
        for candidate in (parent / name for parent in parents):
            if not candidate.exists():
                continue
            if directories is True and not candidate.is_dir():
                continue
            if directories is False and not candidate.is_file():
                continue
            relative = candidate.relative_to(root)
            if relative.parts and relative.parts[0] in IGNORED_TOP_LEVEL:
                continue
            matches.add(candidate)
    return sorted(path.relative_to(root).as_posix() for path in matches)


def _git_summary(root: Path) -> dict[str, Any]:
    if not (root / ".git").exists():
        return {"repository": False, "branch": None, "changed_files": 0}
    try:
        branch = subprocess.run(
            ["git", "-C", str(root), "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {"repository": True, "branch": None, "changed_files": None}
    return {
        "repository": True,
        "branch": (branch.stdout.strip() or None) if branch.returncode == 0 else None,
        "changed_files": (
            len([line for line in status.stdout.splitlines() if line.strip()])
            if status.returncode == 0 else None
        ),
    }


def inspect_project(workspace: str | Path, *, include_git: bool = True) -> dict[str, Any]:
    """Return bounded evidence; skipped Git is explicitly unknown, not clean."""

    root = Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Workspace does not exist: {root}")

    visible = [item for item in root.iterdir() if item.name not in IGNORED_TOP_LEVEL]
    # Enumerate candidate parents once, pruning ignored roots before traversal.
    # Preserve the original root / */ / */*/ marker depth, not a recursive walk.
    parents = [root]
    for item in visible:
        if item.is_dir():
            parents.append(item)
            try:
                parents.extend(child for child in item.iterdir() if child.is_dir())
            except OSError:
                # Path.glob previously skipped unreadable nested directories.
                continue
    manifests = _relative_markers(root, MANIFEST_NAMES, parents=parents, directories=False)
    sources = _relative_markers(root, SOURCE_NAMES, parents=parents, directories=True)
    tests = _relative_markers(root, TEST_NAMES, parents=parents, directories=True)
    locks = _relative_markers(root, LOCK_NAMES, parents=parents, directories=False)
    readme = any((root / name).is_file() for name in ("README.md", "README.rst", "README.txt"))
    license_file = any((root / name).is_file() for name in ("LICENSE", "LICENSE.md", "COPYING"))
    changelog = any((root / name).is_file() for name in ("CHANGELOG.md", "CHANGES.md", "HISTORY.md"))
    security = any((root / name).is_file() for name in ("SECURITY.md", ".github/SECURITY.md"))
    workflows = root / ".github" / "workflows"
    ci = workflows.is_dir() and any(path.suffix in {".yml", ".yaml"} for path in workflows.iterdir())
    release_docs = sum((readme, license_file, changelog, security))

    if not visible:
        stage = "idea"
        next_steps = ["Define the smallest useful outcome", "Choose one implementation stack", "Create the first runnable project"]
    elif not manifests:
        stage = "discovery"
        next_steps = ["Identify the project entrypoint and technology", "Document how to start it", "Choose one small verified change"]
    elif not sources:
        stage = "setup"
        next_steps = ["Create the first runnable feature", "Add a repeatable start command", "Record the expected behavior"]
    elif not tests:
        stage = "building"
        next_steps = ["Finish one end-to-end user scenario", "Add the smallest automated verification", "Document how to run it"]
    elif not ci or release_docs < 3:
        stage = "validation"
        next_steps = ["Run the relevant tests", "Add missing release and recovery documentation", "Automate checks in CI"]
    else:
        stage = "release_candidate"
        next_steps = ["Run the full release gate", "Test a clean installation and uninstall", "Resolve every blocking issue before publishing"]

    evidence = {
        "top_level_items": len(visible),
        "manifests": manifests,
        "source_roots": sources,
        "test_roots": tests,
        "lockfiles": locks,
        "readme": readme,
        "license": license_file,
        "changelog": changelog,
        "security_policy": security,
        "ci": ci,
    }
    return {
        "workspace": str(root),
        "stage": stage,
        "stage_is_evidence_only": True,
        "release_ready": False,
        "release_ready_reason": "A file inspection cannot prove that builds, tests, installation, and release gates pass.",
        "evidence": evidence,
        "git": _git_summary(root) if include_git else None,
        "next_steps": next_steps,
        "privacy": "File contents were not read or retained.",
    }
