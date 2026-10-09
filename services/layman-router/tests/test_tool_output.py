from __future__ import annotations

import io
import json

import pytest
from layman_router import cli
from layman_router.tool_output import (
    MAX_CHARS,
    PREFIX,
    compact_output,
    optimize_tool_outputs,
    restore_output,
)


@pytest.mark.parametrize("line", ["progress: unchanged\n", "中文日志\r\n", "warning: `code` \\\" \n", "same\r", "same\u2028"])
def test_repeated_lines_are_smaller_and_exactly_reversible(line):
    raw = "start\n" + line * 100 + "FAILED: keep this diagnostic\nend"
    packed = compact_output(raw)
    assert packed.startswith(PREFIX)
    assert restore_output(packed) == raw
    assert len(packed.encode("utf-8")) < len(raw.encode("utf-8"))
    assert len(json.dumps(packed).encode()) < len(json.dumps(raw).encode())
    assert "FAILED: keep this diagnostic" in packed
    assert compact_output(packed) == packed


@pytest.mark.parametrize("raw", ["", "a\na\n", "unique\nlines", '{"values": [1, 2]}', "x\n" * 2, "no newline", PREFIX + "not JSON"])
def test_nonbeneficial_and_preencoded_text_are_unchanged(raw):
    assert compact_output(raw) == raw


@pytest.mark.parametrize("raw", [json.dumps(["same"] * 100, indent=2), "```text\n" + "log\n" * 100 + "```"])
def test_structured_json_and_fenced_code_are_not_encoded(raw):
    assert compact_output(raw) == raw


@pytest.mark.parametrize("runs", [None, {}, [["x", True]], [["x", 0]], [["x", -1]], [["x", 1.5]], [[5, 2]], [["x", 2, 3]], [["x", MAX_CHARS + 1]], [["", 10**100]]])
def test_invalid_or_expanding_encodings_are_rejected(runs):
    with pytest.raises(ValueError):
        restore_output(PREFIX + json.dumps(runs))


def test_tool_encoding_is_opt_in_auto_only_and_preserves_other_items():
    text = "log\n" * 100
    payload = {"model": "auto", "input": [
        {"type": "function_call_output", "call_id": "c1", "output": text, "status": "failed"},
        {"role": "user", "content": text},
        {"type": "function_call_output", "call_id": "c2", "output": [{"type": "input_image"}]},
        {"type": "function_call", "call_id": "c1", "arguments": text},
    ]}
    for original in (payload, {**payload, "model": "gpt-6-astra", "metadata": {"layman_tool_output_mode": "lossless_lines"}}):
        prepared, report = optimize_tool_outputs(original)
        assert prepared == original
        assert report.mode == "off"
    opted_in = {**payload, "metadata": {"layman_tool_output_mode": "lossless_lines"}}
    prepared, report = optimize_tool_outputs(opted_in)
    assert report.compressed == 1
    assert report.original_bytes == len(text.encode())
    assert report.packed_bytes < report.original_bytes
    assert prepared["input"][0]["status"] == "failed"
    assert prepared["input"][0]["call_id"] == "c1"
    assert restore_output(prepared["input"][0]["output"]) == text
    assert prepared["input"][1:] == payload["input"][1:]
    assert payload["input"][0]["output"] == text


def test_unknown_mode_fails_closed():
    with pytest.raises(ValueError, match="layman_tool_output_mode"):
        optimize_tool_outputs({"model": "auto", "metadata": {"layman_tool_output_mode": "truncate"}})


def test_cli_compacts_and_restores_without_a_model_call(monkeypatch, capsys):
    raw = "warning: retain every occurrence\n" * 100 + "FAILED\n"
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(raw))
    assert cli.main(["compact-output"]) == 0
    packed = capsys.readouterr().out
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(packed))
    assert cli.main(["compact-output", "--restore"]) == 0
    assert capsys.readouterr().out == raw


def test_cli_utf8_binary_wire_preserves_crlf_and_unicode(monkeypatch):
    raw = ("中文 warning\r\n" * 100 + "FAILED\n").encode("utf-8")
    stdin = io.TextIOWrapper(io.BytesIO(raw), encoding="ascii")
    stdout = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
    monkeypatch.setattr(cli, "_configure_windows_stdio", lambda: None)
    monkeypatch.setattr(cli.sys, "stdin", stdin)
    monkeypatch.setattr(cli.sys, "stdout", stdout)
    assert cli.main(["compact-output"]) == 0
    packed = stdout.buffer.getvalue()
    assert restore_output(packed.decode("utf-8")).encode("utf-8") == raw
