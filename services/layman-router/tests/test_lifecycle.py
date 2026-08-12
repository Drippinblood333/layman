from __future__ import annotations

import os
from pathlib import Path

from layman_router.cli import build_parser
from layman_router.paths import migrate_legacy_data, read_state
from layman_router.lifecycle import _is_running, setup_state


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
