from __future__ import annotations

import json
import os
import subprocess
import sys
from io import BytesIO, StringIO, TextIOWrapper
from types import SimpleNamespace

import pytest
from layman_router import cli


@pytest.mark.parametrize("argv", [[], None])
def test_no_arguments_show_safe_first_step_without_starting_work(monkeypatch, capsys, argv):
    monkeypatch.setattr(sys, "argv", ["layman"])
    for name in ("_input_task", "load_config", "find_codex", "run_plus_task", "setup_state"):
        monkeypatch.setattr(cli, name, lambda *a, **k: pytest.fail("Welcome must not start work or setup"))
    assert cli.main(argv) == 0
    captured = capsys.readouterr()
    assert "layman plan --brief" in captured.out
    assert "No task has started" in captured.out
    assert "layman --help" in captured.out
    assert captured.err == ""
    assert len(captured.out.splitlines()) <= 3


def test_no_argument_cli_does_not_need_config_login_or_read_piped_task(tmp_path):
    home = tmp_path / "unused-home"
    codex_home = tmp_path / "unused-codex-home"
    result = subprocess.run([sys.executable, "-m", "layman_router.cli"],
        input=b"private-piped-task-must-not-appear", capture_output=True, timeout=15, check=False,
        cwd=tmp_path, env={**os.environ, "LAYMAN_HOME": str(home), "CODEX_HOME": str(codex_home),
            "LAYMAN_ROUTER_CONFIG": str(tmp_path / "absent-config.yaml")})
    assert result.returncode == 0
    assert b"layman plan --brief" in result.stdout
    assert b"private-piped-task" not in result.stdout + result.stderr
    assert result.stderr == b""
    assert not home.exists() and not codex_home.exists()


@pytest.mark.parametrize("argv,code", [(["--help"], 0), (["--unknown-option"], 2)])
def test_explicit_help_and_invalid_options_keep_parser_behavior(capsys, argv, code):
    with pytest.raises(SystemExit) as error:
        cli.main(argv)
    assert error.value.code == code
    captured = capsys.readouterr()
    assert "No task has started" not in captured.out + captured.err


def test_clipboard_input_preserves_unicode(monkeypatch):
    monkeypatch.setattr(cli, "_clipboard_task", lambda: "增加一个设置页面")
    assert cli._input_task(clipboard=True) == "增加一个设置页面"


def test_piped_task_reads_utf8_bytes_not_locale_text(monkeypatch):
    task = "只读分析 README.md，不要修改文件。"
    stream = TextIOWrapper(BytesIO(task.encode("utf-8")), encoding="cp1252", errors="surrogateescape")
    monkeypatch.setattr(cli.sys, "stdin", stream)
    assert cli._input_task() == task


def test_invalid_piped_utf8_is_rejected_before_planning(monkeypatch, capsys):
    stream = TextIOWrapper(BytesIO(b"\xff"), encoding="cp1252")
    monkeypatch.setattr(cli.sys, "stdin", stream)
    monkeypatch.setattr(cli, "create_task_plan", lambda *a: pytest.fail("Invalid input must stop before planning"))
    assert cli.main(["plan"]) == 1
    assert "utf-8" in capsys.readouterr().err


def test_public_cli_exposes_beginner_entry_points():
    parser = cli.build_parser()
    assert parser.parse_args(["status"]).command == "status"
    assert parser.parse_args(["plan", "--clipboard"]).clipboard is True
    assert parser.parse_args(["run", "--dry-run", "--clipboard"]).clipboard is True


@pytest.mark.parametrize("mode", ["plus", "auto"])
@pytest.mark.parametrize("skip_plugin", [False, True])
def test_plus_setup_start_rejected_before_setup_mutations(monkeypatch, capsys, mode, skip_plugin):
    monkeypatch.setattr(cli, "detect_user_mode", lambda: ("plus", {"codex_path": "synthetic-codex"}))
    monkeypatch.setattr(cli, "read_state", lambda: pytest.fail("Invalid flags must stop before state access"))
    monkeypatch.setattr(cli, "setup_state", lambda *a: pytest.fail("Invalid flags must not initialize state"))
    monkeypatch.setattr(cli, "install_codex_plugin", lambda: pytest.fail("Invalid flags must not install plugins"))
    monkeypatch.setattr(cli, "start_router", lambda: pytest.fail("Invalid flags must not start a service"))
    args = ["setup", "--mode", mode, "--start"] + (["--skip-plugin"] if skip_plugin else [])
    assert cli.main(args) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "HTTP router requires API mode" in captured.err


@pytest.mark.parametrize("mode", ["api", "auto"])
def test_api_setup_start_still_starts_requested_service(monkeypatch, capsys, mode):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-not-a-key")
    monkeypatch.setattr(cli, "detect_user_mode", lambda: ("api", {}))
    monkeypatch.setattr(cli, "read_state", dict)
    monkeypatch.setattr(cli, "setup_state", lambda selected: {"mode": selected})
    monkeypatch.setattr(cli, "write_state", lambda state: None)
    monkeypatch.setattr(cli, "enable_codex", lambda **kw: SimpleNamespace(diff="preview only"))
    calls = []
    monkeypatch.setattr(cli, "start_router", lambda: calls.append("start") or {"running": True})
    assert cli.main(["setup", "--mode", mode, "--start", "--skip-plugin"]) == 0
    assert calls == ["start"]
    assert json.loads(capsys.readouterr().out)["router"] == {"running": True}


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
    stream = StringIO("修复src/a.py的空指针异常，不改接口\n")
    monkeypatch.setattr(stream, "isatty", lambda: True)
    monkeypatch.setattr(cli.sys, "stdin", stream)
    monkeypatch.setattr("layman_router.plus_run.find_codex", lambda *a, **k: pytest.fail("Dry run must not start Codex"))
    assert cli.main(["run", "--dry-run", "--cwd", str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == "dry-run"


def test_plus_status_skips_optional_router_without_claiming_login(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "read_state", lambda: {"mode": "plus"})
    monkeypatch.setattr(cli, "process_status", lambda: {"running": False, "pid": None})
    monkeypatch.setattr(cli, "_fetch", lambda *a, **k: pytest.fail("Plus project status must not probe the API router"))
    monkeypatch.setattr(cli, "find_codex", lambda *a, **k: pytest.fail("Status must not infer ChatGPT login"))
    assert cli.main(["status", "--cwd", str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["configured_mode"] == "plus"
    assert result["router"]["service"] == {"status": "not_checked", "required": False}
    assert "login is not checked" in result["meaning"]


@pytest.mark.parametrize("available,chatgpt,expected_exit", [(True, True, 0), (True, False, 1), (False, False, 1)])
def test_plus_doctor_checks_login_without_requesting_api_service(monkeypatch, capsys, available, chatgpt, expected_exit):
    monkeypatch.setattr(cli, "read_state", lambda: {"mode": "plus"})
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(cli, "find_codex", lambda: "synthetic-codex")
    monkeypatch.setattr(cli, "codex_login_status", lambda path: {
        "available": available, "chatgpt_login": chatgpt, "status": "private diagnostic",
    })
    monkeypatch.setattr(cli, "_fetch", lambda *a, **k: pytest.fail("Plus doctor must not require the API router"))
    monkeypatch.setattr(cli, "_writable_ancestor", lambda *a: pytest.fail("Plus doctor must not require an API database"))
    assert cli.main(["doctor"]) == expected_exit
    result = json.loads(capsys.readouterr().out)
    assert result["configured_mode"] == "plus"
    assert result["openai_api_key"] == result["admin_token"] == "not_required"
    assert result["service"] == "not_required"
    assert result["codex_cli"] == "available"
    assert result["chatgpt_login"] == ("credentials_present" if available and chatgpt else "not_detected")
    assert "sandboxed execution are not verified" in result["meaning"]
    assert "private diagnostic" not in json.dumps(result)


def test_plus_doctor_missing_cli_is_actionable_without_configuration_writes(monkeypatch, capsys):
    monkeypatch.setattr(cli, "read_state", lambda: {"mode": "plus"})
    monkeypatch.setattr(cli, "find_codex", lambda: (_ for _ in ()).throw(FileNotFoundError("private path")))
    monkeypatch.setattr(cli, "codex_login_status", lambda *a: pytest.fail("No executable to check"))
    monkeypatch.setattr(cli, "_fetch", lambda *a: pytest.fail("No API service needed"))
    monkeypatch.setattr(cli, "write_state", lambda *a: pytest.fail("Doctor must not write state"))
    assert cli.main(["doctor"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["codex_cli"] == "unavailable"
    assert result["chatgpt_login"] == "not_detected"
    assert "Install Codex CLI" in result["next_step"]
    assert "private path" not in json.dumps(result)


def test_plus_doctor_still_rejects_invalid_shared_routing_config(monkeypatch, capsys):
    monkeypatch.setattr(cli, "read_state", lambda: {"mode": "plus"})
    monkeypatch.setattr(cli, "load_config", lambda: (_ for _ in ()).throw(ValueError("invalid routing configuration")))
    monkeypatch.setattr(cli, "find_codex", lambda: pytest.fail("Invalid configuration must stop before login checks"))
    assert cli.main(["doctor"]) == 1
    assert "invalid routing configuration" in capsys.readouterr().err


@pytest.mark.parametrize("mode", ["api", None, []])
def test_doctor_preserves_api_or_unknown_mode_checks(monkeypatch, capsys, mode):
    monkeypatch.setattr(cli, "read_state", lambda: {"mode": mode})
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(cli, "_writable_ancestor", lambda *a: True)
    monkeypatch.setattr(cli, "find_codex", lambda: pytest.fail("API doctor does not inspect Plus login"))
    monkeypatch.setattr(cli, "_fetch", lambda *a: {"status": "ok"})
    assert cli.main(["doctor"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["database_parent_writable"] is True
    assert result["openai_api_key"] == "missing"
    assert result["service"] == "ok"


@pytest.mark.parametrize("mode,service_only", [
    ("api", False), (None, False), ([], False), ({"unexpected": "plus"}, False), ("plus", True),
])
def test_status_keeps_explicit_or_non_plus_service_probe(monkeypatch, tmp_path, capsys, mode, service_only):
    monkeypatch.setattr(cli, "read_state", lambda: {"mode": mode})
    monkeypatch.setattr(cli, "process_status", lambda: {"running": False, "pid": None})
    requests = []

    def offline(path):
        requests.append(path)
        raise OSError("synthetic service offline")

    monkeypatch.setattr(cli, "_fetch", offline)
    args = ["status", "--cwd", str(tmp_path)] + (["--service-only"] if service_only else [])
    assert cli.main(args) == 0
    result = json.loads(capsys.readouterr().out)
    router = result if service_only else result["router"]
    assert router["service"] == {"status": "offline"}
    assert requests == ["/healthz"]
    if not service_only:
        assert result["configured_mode"] == ("api" if mode == "api" else "unknown")


@pytest.mark.parametrize("task", [
    "Fix src/login.py null handling; preserve the API",
    "帮我优化整个项目",
    "只读分析 README.md，不要修改文件。",
    "请删除生产支付数据库并迁移权限",
])
def test_brief_plan_retains_actionable_guidance_without_execution(monkeypatch, tmp_path, capsys, task):
    from layman_router.task_plan import create_task_plan

    plan = create_task_plan(task, tmp_path)
    original = json.dumps(plan, ensure_ascii=False)
    monkeypatch.setattr(cli, "_input_task", lambda **kwargs: task)
    monkeypatch.setattr(cli, "create_task_plan", lambda *args: plan)
    monkeypatch.setattr(cli, "run_plus_task", lambda *args, **kwargs: pytest.fail("Plan must not execute"))
    assert cli.main(["plan", "--brief", "--cwd", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "No execution started" in output
    assert plan["route"]["sandbox"] in output
    assert plan["execution"] in output
    assert plan["risk"] in output
    for section in ("next_steps", "acceptance_criteria", "stop_conditions"):
        assert all(item in output for item in plan[section])
    assert all(question in output for question in plan["prompt_guidance"]["questions"])
    assert "router_compute_ms" not in output
    assert "routing_decision" not in output
    assert task not in output
    assert json.dumps(plan, ensure_ascii=False) == original
    assert f"{plan['route']['initial_file_budget']} initially" in output
    assert f"{plan['route']['expanded_file_budget']} expanded" in output
    assert f"tool-call budget: {plan['route']['tool_call_budget']}" in output


def test_plan_default_output_remains_json(monkeypatch, tmp_path, capsys):
    task = "Fix src/login.py null handling"
    monkeypatch.setattr(cli, "_input_task", lambda **kwargs: task)
    assert cli.main(["plan", "--cwd", str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert "routing_decision" in result["route"]
    assert result["stores_task_or_code"] is False


def test_offline_plan_does_not_import_api_server(tmp_path):
    code = (
        "import sys\n"
        "class BlockServer:\n"
        " def find_spec(self, fullname, path=None, target=None):\n"
        "  if fullname == 'uvicorn' or fullname.startswith('uvicorn.'):\n"
        "   raise ImportError('Offline plan imported the API server')\n"
        "sys.meta_path.insert(0, BlockServer())\n"
        "from layman_router.cli import main\n"
        "raise SystemExit(main(['plan', '--brief']))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path,
        input="只读分析 README.md，不要修改文件。", capture_output=True,
        encoding="utf-8", timeout=20, check=False,
        env={**os.environ, "PYTHONUTF8": "0", "PYTHONIOENCODING": "cp1252:surrogateescape"},
    )
    assert result.returncode == 0, result.stderr
    assert "No execution started" in result.stdout
    assert "read-only" in result.stdout


@pytest.mark.parametrize("command,port", [(["serve"], 8765), (["demo", "--port", "8765"], 8765)])
def test_server_commands_still_load_and_delegate_to_uvicorn(monkeypatch, tmp_path, command, port):
    calls = []
    server = SimpleNamespace(run=lambda *a, **k: calls.append((a, k)))
    monkeypatch.setitem(sys.modules, "uvicorn", server)
    monkeypatch.setattr(cli, "uvicorn", server, raising=False)
    monkeypatch.setattr(cli, "load_config", lambda: SimpleNamespace(
        listen_host="127.0.0.1", listen_port=port,
        admin_token_env="LAYMAN_TEST_DEMO_TOKEN", database_path=tmp_path / "demo.sqlite3",
    ))
    monkeypatch.setitem(sys.modules, "layman_router.demo", SimpleNamespace(seed_demo=lambda *a: None))
    monkeypatch.setitem(sys.modules, "layman_router.telemetry", SimpleNamespace(
        UsageStore=lambda *a: SimpleNamespace(initialize=lambda: None),
    ))
    for name in ("LAYMAN_ROUTER_DEMO", "LAYMAN_ROUTER_PORT", "LAYMAN_ROUTER_DATABASE_PATH", "LAYMAN_TEST_DEMO_TOKEN"):
        monkeypatch.setenv(name, "synthetic-before")
    assert cli.main(command) == 0
    assert calls == [(("layman_router.app:create_app",), {
        "factory": True, "host": "127.0.0.1", "port": port,
    })]
