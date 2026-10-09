from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


def load_smoke():
    path = Path(__file__).resolve().parents[3] / "scripts" / "smoke-python-packages.py"
    spec = importlib.util.spec_from_file_location("package_smoke_isolation_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_child_environment_excludes_credentials_without_changing_parent(tmp_path):
    smoke = load_smoke()
    inherited = {key: "synthetic-credential" for key in smoke.SMOKE_BLOCKED_ENV_VARS}
    inherited.update({"openai_api_key": "synthetic-lowercase", "LAYMAN_ROUTER_CONFIG": "host-config", "PATH": "runtime-path"})
    before = inherited.copy()
    environment = smoke.smoke_environment(tmp_path, inherited)
    assert inherited == before
    assert environment == {
        "PATH": "runtime-path",
        "LAYMAN_HOME": str(tmp_path / "layman-home"),
        "LAYMAN_ROUTER_DATABASE_PATH": str(tmp_path / "layman-home" / "usage.sqlite3"),
    }


def test_smoke_subprocess_uses_explicit_temporary_working_directory(tmp_path, monkeypatch):
    smoke = load_smoke()
    seen = []

    def runner(command, **kwargs):
        seen.append(kwargs)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(smoke.subprocess, "run", runner)
    smoke.run(["fake-python", "--help"], environment={"PATH": "runtime-path"}, cwd=tmp_path)
    assert seen[0]["cwd"] == tmp_path
    assert seen[0]["env"] == {"PATH": "runtime-path"}
