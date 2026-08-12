from __future__ import annotations

import layman_router.cli as cli


def test_clipboard_input_preserves_unicode(monkeypatch):
    monkeypatch.setattr(cli, "_clipboard_task", lambda: "增加一个设置页面")
    assert cli._input_task(clipboard=True) == "增加一个设置页面"


def test_public_cli_exposes_beginner_entry_points():
    parser = cli.build_parser()
    assert parser.parse_args(["status"]).command == "status"
    assert parser.parse_args(["plan", "--clipboard"]).clipboard is True
    assert parser.parse_args(["run", "--dry-run", "--clipboard"]).clipboard is True
