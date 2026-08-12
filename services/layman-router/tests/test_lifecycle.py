from __future__ import annotations

import os
import subprocess
from pathlib import Path

from layman_router.cli import build_parser, main
from layman_router.paths import migrate_legacy_data, read_state
from layman_router.lifecycle import (
    _is_running,
    detect_user_mode,
    install_codex_plugin,
    remove_codex_plugin,
    setup_state,
)


def test_public_cli_contains_v3_commands():
    parser = build_parser()
    for command in ("setup", "start", "stop", "status", "doctor", "dashboard", "report", "uninstall"):
        args = parser.parse_args([command])
        assert args.command == command


def test_process_liveness_detects_current_and_missing_process():
    assert _is_running(os.getpid()) is True
    assert _is_running(999_999_999) is False


def test_legacy_migration_copies_without_deleting(monkeypatch, tmp_path: Path):
    old = tmp_path / "legacy"
    new = tmp_path / "current"
    old.mkdir()
    (old / "usage.sqlite3").write_bytes(b"legacy-db")
    monkeypatch.setenv("LAYMAN_HOME", str(new))
    monkeypatch.setattr("layman_router.paths.legacy_home", lambda: old)
    copied = migrate_legacy_data()
    assert copied == [(old / "usage.sqlite3", new / "usage.sqlite3")]
    assert (new / "usage.sqlite3").read_bytes() == b"legacy-db"
    assert (old / "usage.sqlite3").exists()


def test_setup_state_generates_private_local_token(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LAYMAN_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("layman_router.paths.legacy_home", lambda: tmp_path / "missing")
    state = setup_state("plus")
    assert state["mode"] == "plus"
    assert len(state["admin_token"]) >= 32
    assert read_state()["admin_token"] == state["admin_token"]


def test_remove_codex_plugin_removes_plugin_before_marketplace(monkeypatch):
    monkeypatch.setattr("layman_router.lifecycle.find_codex", lambda: "codex.exe")
    calls = []

    def fake_runner(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    result = remove_codex_plugin(runner=fake_runner)
    assert calls == [
        ["codex.exe", "plugin", "remove", "layman@layman-local", "--json"],
        ["codex.exe", "plugin", "marketplace", "remove", "layman-local", "--json"],
    ]
    assert result["removed"] is True


def test_install_codex_plugin_creates_configured_codex_home(monkeypatch, tmp_path: Path):
    bundle = tmp_path / "bundle"
    manifest = bundle / ".agents" / "plugins" / "marketplace.json"
    plugin = bundle / "plugins" / "layman"
    manifest.parent.mkdir(parents=True)
    plugin.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    (plugin / ".mcp.json").write_text("{}", encoding="utf-8")
    codex_home = tmp_path / "new-codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("LAYMAN_HOME", str(tmp_path / "layman-home"))
    monkeypatch.setattr("layman_router.lifecycle._bundle_root", lambda: bundle)
    monkeypatch.setattr("layman_router.lifecycle.find_codex", lambda: "codex.exe")
    monkeypatch.setattr(
        "layman_router.lifecycle.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, stdout="{}", stderr=""),
    )

    assert install_codex_plugin()["installed"] is True
    assert codex_home.is_dir()


def test_mode_detection_creates_configured_codex_home(monkeypatch, tmp_path: Path):
    codex_home = tmp_path / "new-codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("layman_router.lifecycle.find_codex", lambda: "codex.exe")
    monkeypatch.setattr(
        "layman_router.lifecycle.codex_login_status",
        lambda executable: {"available": True, "chatgpt_login": True, "status": "ok"},
    )

    mode, details = detect_user_mode()
    assert mode == "plus"
    assert details["codex_login"]["chatgpt_login"] is True
    assert codex_home.is_dir()


def test_remove_codex_plugin_tolerates_absent_marketplace(monkeypatch):
    monkeypatch.setattr("layman_router.lifecycle.find_codex", lambda: "codex.exe")

    def fake_runner(command, **kwargs):
        if command[2:4] == ["marketplace", "remove"]:
            return subprocess.CompletedProcess(
                command, 1, stdout="", stderr="marketplace is not configured or installed"
            )
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    assert remove_codex_plugin(runner=fake_runner)["removed"] is True


def test_purge_refuses_to_delete_data_when_codex_references_cannot_be_removed(monkeypatch, tmp_path: Path):
    home = tmp_path / "layman-home"
    home.mkdir()
    (home / "state.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("layman_router.cli.stop_router", lambda: {"running": False, "stopped": False})
    monkeypatch.setattr("layman_router.cli.layman_home", lambda: home)

    def missing_codex():
        raise FileNotFoundError("Codex CLI not found")

    monkeypatch.setattr("layman_router.cli.remove_codex_plugin", missing_codex)
    assert main(["uninstall", "--purge-data"]) == 1
    assert (home / "state.json").exists()
