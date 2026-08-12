from __future__ import annotations

from pathlib import Path

from layman_router.project_status import inspect_project


def test_empty_workspace_is_idea_stage(tmp_path: Path):
    result = inspect_project(tmp_path)
    assert result["stage"] == "idea"
    assert result["release_ready"] is False
    assert result["evidence"]["manifests"] == []


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
