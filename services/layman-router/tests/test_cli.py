from __future__ import annotations

from io import StringIO

import pytest
from layman_router import cli


def test_clipboard_input_preserves_unicode(monkeypatch):
    monkeypatch.setattr(cli, "_clipboard_task", lambda: "增加一个设置页面")
    assert cli._input_task(clipboard=True) == "增加一个设置页面"


def test_public_cli_exposes_beginner_entry_points():
    parser = cli.build_parser()
    assert parser.parse_args(["status"]).command == "status"
    assert parser.parse_args(["plan", "--clipboard"]).clipboard is True
    assert parser.parse_args(["run", "--dry-run", "--clipboard"]).clipboard is True


def test_terminal_input_preserves_intent_without_polluting_stdout(monkeypatch, capsys):
    task = " 修复登录报错，不改接口 "
    stream = StringIO(task + "\r\nsecond line\n")
    monkeypatch.setattr(stream, "isatty", lambda: True)
    monkeypatch.setattr(cli.sys, "stdin", stream)
    assert cli._input_task() == task
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "输入一行需求" in captured.err
    assert task not in captured.err
    assert stream.read() == "second line\n"


@pytest.mark.parametrize("text", ["", "\n", "  \n"])
def test_empty_terminal_input_does_not_start_a_task(monkeypatch, text):
    stream = StringIO(text)
    monkeypatch.setattr(stream, "isatty", lambda: True)
    monkeypatch.setattr(cli.sys, "stdin", stream)
    with pytest.raises(RuntimeError, match="must not be empty"):
        cli._input_task()


def test_piped_multiline_input_stays_unchanged_and_silent(monkeypatch, capsys):
    task = "修复登录报错\n不要修改接口\n"
    monkeypatch.setattr(cli.sys, "stdin", StringIO("\ufeff" + task))
    assert cli._input_task() == task
    assert capsys.readouterr().err == ""


def test_interactive_dry_run_never_starts_codex(monkeypatch, tmp_path, capsys):
    import json

    stream = StringIO("修复src/a.py的空指针异常，不改接口\n")
    monkeypatch.setattr(stream, "isatty", lambda: True)
    monkeypatch.setattr(cli.sys, "stdin", stream)
    monkeypatch.setattr("layman_router.plus_run.find_codex", lambda *a, **k: pytest.fail("Dry run must not start Codex"))
    assert cli.main(["run", "--dry-run", "--cwd", str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == "dry-run"
