from __future__ import annotations

import os
import json
import subprocess
from pathlib import Path

from layman_router.cli import build_parser, main
from layman_router.paths import OWNERSHIP_MARKER, mark_layman_home_owned, migrate_legacy_data, read_state
from layman_router.lifecycle import (
    _is_running,
    detect_user_mode,
    install_codex_plugin,
    remove_codex_plugin,
    process_status,
    setup_state,
    stop_router,
)


def test_public_cli_contains_v3_commands():
    parser = build_parser()
    for command in ("setup", "start", "stop", "status", "doctor", "dashboard", "report", "uninstall"):
        args = parser.parse_args([command])
        assert args.command == command


def test_public_cli_exposes_version(capsys):
    try:
        build_parser().parse_args(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert capsys.readouterr().out.strip() == "layman 1.0.0"


def test_plus_eval_defaults_respect_layman_home(monkeypatch, tmp_path: Path):
    home = tmp_path / "custom-layman"
    monkeypatch.setenv("LAYMAN_HOME", str(home))
    args = build_parser().parse_args(["codex-plus", "eval"])
    assert args.output == home / "plus-eval.jsonl"
    assert args.workspace == home / "plus-workspace"


def test_process_liveness_detects_current_and_missing_process():
    assert _is_running(os.getpid()) is True
    assert _is_running(999_999_999) is False


def test_process_status_verifies_process_creation_token(monkeypatch, tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    (home / "router.pid").write_text(
        json.dumps({"format": 1, "pid": 123, "start_token": "test:created"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("LAYMAN_HOME", str(home))
    monkeypatch.setattr("layman_router.lifecycle._is_running", lambda pid: True)
    monkeypatch.setattr("layman_router.lifecycle._process_start_token", lambda pid: "test:created")

    status = process_status()
    assert status["running"] is True
    assert status["identity_verified"] is True


def test_stop_refuses_reused_or_unverified_pid(monkeypatch, tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    pid_path = home / "router.pid"
    pid_path.write_text(
        json.dumps({"format": 1, "pid": 123, "start_token": "test:old"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("LAYMAN_HOME", str(home))
    monkeypatch.setattr("layman_router.lifecycle._is_running", lambda pid: True)
    monkeypatch.setattr("layman_router.lifecycle._process_start_token", lambda pid: "test:new")
    monkeypatch.setattr(
        "layman_router.lifecycle.os.kill",
        lambda pid, sig: (_ for _ in ()).throw(AssertionError("must not signal an unverified PID")),
    )

    result = stop_router()
    assert result["stopped"] is False
    assert "no signal" in result["refused"]
    assert pid_path.exists()


def test_stop_terminates_only_a_verified_process_tree(monkeypatch, tmp_path: Path):
    home = tmp_path / "layman"
    home.mkdir()
    pid_path = home / "router.pid"
    pid_path.write_text(
        json.dumps({"format": 1, "pid": 123, "start_token": "test:same"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("LAYMAN_HOME", str(home))
    running = iter((True, False, False))
    monkeypatch.setattr("layman_router.lifecycle._is_running", lambda pid: next(running))
    monkeypatch.setattr(
        "layman_router.lifecycle._process_start_token", lambda pid: "test:same"
    )
    calls: list[tuple[int, bool]] = []
    monkeypatch.setattr(
        "layman_router.lifecycle._terminate_router_tree",
        lambda pid, force=False: calls.append((pid, force)),
    )

    result = stop_router()

    assert result == {"running": False, "stopped": True, "pid": 123}
    assert calls == [(123, False)]
    assert not pid_path.exists()


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
    assert (tmp_path / "home" / OWNERSHIP_MARKER).is_file()


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


def test_purge_skips_codex_removal_when_plugin_was_explicitly_skipped(monkeypatch, tmp_path: Path):
    home = tmp_path / "layman-home"
    mark_layman_home_owned(home)
    (home / "state.json").write_text('{"codex_plugin_managed": false}', encoding="utf-8")
    monkeypatch.setenv("LAYMAN_HOME", str(home))
    monkeypatch.setattr("layman_router.cli.stop_router", lambda: {"running": False, "stopped": False})
    monkeypatch.setattr(
        "layman_router.cli.remove_codex_plugin",
        lambda: (_ for _ in ()).throw(AssertionError("Codex removal must be skipped")),
    )
    monkeypatch.setattr(
        "layman_router.cli.disable_codex",
        lambda **kwargs: (_ for _ in ()).throw(FileNotFoundError("no Codex config")),
    )

    assert main(["uninstall", "--purge-data"]) == 0
    assert not home.exists()


def test_purge_refuses_unowned_custom_home(monkeypatch, tmp_path: Path):
    home = tmp_path / "documents"
    home.mkdir()
    unrelated = home / "family-photo.txt"
    unrelated.write_text("keep", encoding="utf-8")
    monkeypatch.setenv("LAYMAN_HOME", str(home))
    monkeypatch.setattr("layman_router.cli.stop_router", lambda: {"running": False, "stopped": False})
    monkeypatch.setattr("layman_router.cli.read_state", lambda: {"codex_plugin_managed": False})
    monkeypatch.setattr("layman_router.cli.disable_codex", lambda **kwargs: (_ for _ in ()).throw(FileNotFoundError()))

    assert main(["uninstall", "--purge-data"]) == 1
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_purge_refuses_owned_home_with_unrelated_entries(monkeypatch, tmp_path: Path):
    home = tmp_path / "layman-home"
    mark_layman_home_owned(home)
    (home / "state.json").write_text('{"codex_plugin_managed": false}', encoding="utf-8")
    unrelated = home / "notes.txt"
    unrelated.write_text("keep", encoding="utf-8")
    monkeypatch.setenv("LAYMAN_HOME", str(home))
    monkeypatch.setattr("layman_router.cli.stop_router", lambda: {"running": False, "stopped": False})
    monkeypatch.setattr("layman_router.cli.disable_codex", lambda **kwargs: (_ for _ in ()).throw(FileNotFoundError()))

    assert main(["uninstall", "--purge-data"]) == 1
    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert (home / OWNERSHIP_MARKER).exists()


def test_purge_refuses_preexisting_even_empty_custom_home(monkeypatch, tmp_path: Path):
    home = tmp_path / "preexisting"
    home.mkdir()
    mark_layman_home_owned(home)
    (home / "state.json").write_text('{"codex_plugin_managed": false}', encoding="utf-8")
    monkeypatch.setenv("LAYMAN_HOME", str(home))
    monkeypatch.setattr("layman_router.cli.stop_router", lambda: {"running": False, "stopped": False})
    monkeypatch.setattr("layman_router.cli.disable_codex", lambda **kwargs: (_ for _ in ()).throw(FileNotFoundError()))

    assert main(["uninstall", "--purge-data"]) == 1
    assert (home / "state.json").exists()


def test_skip_plugin_preserves_an_existing_managed_plugin_state(monkeypatch, tmp_path: Path):
    home = tmp_path / "layman-home"
    home.mkdir()
    (home / "state.json").write_text('{"codex_plugin_managed": true}', encoding="utf-8")
    monkeypatch.setenv("LAYMAN_HOME", str(home))
    monkeypatch.setattr("layman_router.paths.legacy_home", lambda: tmp_path / "missing")
    monkeypatch.setattr(
        "layman_router.cli.detect_user_mode",
        lambda: ("plus", {"codex_login": {"available": False}}),
    )
    monkeypatch.setattr(
        "layman_router.cli.find_codex",
        lambda: (_ for _ in ()).throw(FileNotFoundError("no Codex")),
    )

    assert main(["setup", "--mode", "plus", "--skip-plugin"]) == 0
    assert read_state()["codex_plugin_managed"] is True


def test_skip_plugin_keeps_legacy_install_state_conservative(monkeypatch, tmp_path: Path):
    home = tmp_path / "layman-home"
    home.mkdir()
    (home / "state.json").write_text('{"mode": "plus"}', encoding="utf-8")
    monkeypatch.setenv("LAYMAN_HOME", str(home))
    monkeypatch.setattr("layman_router.paths.legacy_home", lambda: tmp_path / "missing")
    monkeypatch.setattr(
        "layman_router.cli.detect_user_mode",
        lambda: ("plus", {"codex_login": {"available": False}}),
    )
    monkeypatch.setattr(
        "layman_router.cli.find_codex",
        lambda: (_ for _ in ()).throw(FileNotFoundError("no Codex")),
    )

    assert main(["setup", "--mode", "plus", "--skip-plugin"]) == 0
    assert "codex_plugin_managed" not in read_state()
