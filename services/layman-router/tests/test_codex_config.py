from __future__ import annotations

from pathlib import Path

import tomlkit

from layman_router.codex_config import disable_codex, enable_codex, list_backups, restore_backup


def test_codex_enable_dry_run_does_not_write(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    original = 'model = "gpt-original"\nmodel_reasoning_effort = "high"\n'
    config_path.write_text(original, encoding="utf-8")
    change = enable_codex(apply=False, home=tmp_path)
    assert change.changed
    assert '+model = "auto"' in change.diff
    assert config_path.read_text(encoding="utf-8") == original
    assert not (tmp_path / "layman-router-state.json").exists()


def test_codex_enable_and_disable_restore_only_managed_values(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('model = "gpt-original"\nmodel_reasoning_effort = "high"\n[features]\napps = true\n', encoding="utf-8")
    enabled = enable_codex(apply=True, home=tmp_path)
    assert enabled.backup_path and enabled.backup_path.exists()
    document = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    assert document["model"] == "auto"
    assert document["model_provider"] == "layman-router"
    assert document["model_providers"]["layman-router"]["wire_api"] == "responses"
    assert document["features"]["apps"] is True

    disable_codex(apply=True, home=tmp_path)
    restored = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    assert restored["model"] == "gpt-original"
    assert "model_provider" not in restored
    assert restored["model_reasoning_effort"] == "high"
    assert restored["features"]["apps"] is True
    assert not (tmp_path / "layman-router-state.json").exists()


def test_disable_preserves_user_change_and_keeps_recovery_state(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('model = "original"\n', encoding="utf-8")
    enable_codex(apply=True, home=tmp_path)
    document = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    document["model"] = "user-changed-model"
    config_path.write_text(tomlkit.dumps(document), encoding="utf-8")
    change = disable_codex(apply=True, home=tmp_path)
    restored = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    assert restored["model"] == "user-changed-model"
    assert change.conflicts
    assert (tmp_path / "layman-router-state.json").exists()


def test_restore_backup_requires_scoped_valid_backup(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('model = "original"\n', encoding="utf-8")
    enable_codex(apply=True, home=tmp_path)
    backup = list_backups(tmp_path)[0]
    config_path.write_text('model = "broken-choice"\n', encoding="utf-8")
    preview = restore_backup(backup, apply=False, home=tmp_path)
    assert preview.changed
    restore_backup(backup, apply=True, home=tmp_path)
    assert tomlkit.parse(config_path.read_text(encoding="utf-8"))["model"] == "original"
