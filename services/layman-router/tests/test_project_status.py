from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from layman_router.project_status import inspect_project


def test_empty_workspace_is_idea_stage(tmp_path: Path):
    result = inspect_project(tmp_path)
    assert result["stage"] == "idea"
    assert result["release_ready"] is False
    assert result["evidence"]["manifests"] == []


def test_marker_depth_and_nested_project_evidence_are_preserved(tmp_path):
    for folder in (tmp_path, tmp_path / "services", tmp_path / "services" / "api"):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "pyproject.toml").write_text("", encoding="utf-8")
    nested = tmp_path / "services" / "api"
    for name in ("src", "tests"):
        (nested / name).mkdir()
    (nested / "requirements.lock").write_text("", encoding="utf-8")
    too_deep = nested / "deeper"
    too_deep.mkdir()
    (too_deep / "package.json").write_text("{}", encoding="utf-8")
    evidence = inspect_project(tmp_path)["evidence"]
    assert evidence["manifests"] == ["pyproject.toml", "services/api/pyproject.toml", "services/pyproject.toml"]
    assert evidence["source_roots"] == ["services", "services/api/src"]
    assert evidence["test_roots"] == ["services/api/tests"]
    assert evidence["lockfiles"] == ["services/api/requirements.lock"]


def test_source_without_tests_is_building_stage(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    result = inspect_project(tmp_path)
    assert result["stage"] == "building"
    assert result["evidence"]["source_roots"] == ["src"]


def test_release_files_make_candidate_but_never_prove_ready(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    for directory in ("src", "tests", ".github/workflows"):
        (tmp_path / directory).mkdir(parents=True)
    (tmp_path / ".github/workflows/ci.yml").write_text("name: CI\n", encoding="utf-8")
    for filename in ("README.md", "LICENSE", "CHANGELOG.md"):
        (tmp_path / filename).write_text(filename, encoding="utf-8")
    result = inspect_project(tmp_path)
    assert result["stage"] == "release_candidate"
    assert result["release_ready"] is False
    assert "cannot prove" in result["release_ready_reason"]


@pytest.mark.parametrize("branch_exit,status_exit", [(0, 128), (128, 0), (128, 128)])
def test_failed_git_commands_report_unknown_not_success(monkeypatch, tmp_path, branch_exit, status_exit):
    (tmp_path / ".git").mkdir()
    responses = iter([
        subprocess.CompletedProcess([], branch_exit, "main\n", "private-error"),
        subprocess.CompletedProcess([], status_exit, " M private-file\n", "private-error"),
    ])
    monkeypatch.setattr("layman_router.project_status.subprocess.run", lambda *a, **k: next(responses))
    result = inspect_project(tmp_path)["git"]
    assert result["branch"] == ("main" if branch_exit == 0 else None)
    assert result["changed_files"] == (1 if status_exit == 0 else None)
    assert "private" not in str(result)


def test_ignored_top_level_directories_are_not_traversed(monkeypatch, tmp_path):
    ignored = tmp_path / "node_modules"
    (ignored / "dependency").mkdir(parents=True)
    (ignored / "dependency" / "package.json").write_text("{}", encoding="utf-8")
    original_scandir = os.scandir

    def guarded_scandir(path):
        if Path(path).is_relative_to(ignored):
            raise AssertionError("Ignored dependency directory was traversed")
        return original_scandir(path)

    monkeypatch.setattr(os, "scandir", guarded_scandir)
    result = inspect_project(tmp_path)
    assert result["stage"] == "idea"
    assert result["evidence"]["manifests"] == []
