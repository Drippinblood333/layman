from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
NOTICES = ("BUILD.json", "bundle-audit.json", "runtime-dependencies.json", "standalone-components.json", "THIRD_PARTY_NOTICES.md")


@pytest.mark.parametrize("missing", [None, "THIRD_PARTY_NOTICES.md", "THIRD_PARTY_LICENSES", "setup_failure"])
def test_installer_preserves_notices_and_refuses_incomplete_package(tmp_path, missing):
    windows = os.name == "nt"
    if missing == "setup_failure" and not windows:
        pytest.skip("PowerShell native exit-status regression")
    shell = (shutil.which("pwsh") or shutil.which("powershell")) if windows else shutil.which("sh")
    if not shell:
        pytest.skip("Native installer shell unavailable")
    home = tmp_path / "profile"
    temporary = tmp_path / "temporary"
    home.mkdir()
    temporary.mkdir()
    executable = "layman.exe" if windows else "layman"
    if windows:
        asset = "layman-windows-x64.zip"
        install_root = home / "Layman" / "bin"
        notice_root = install_root
    else:
        system = "macos" if platform.system() == "Darwin" else "linux"
        arch = "arm64" if platform.machine().lower() in {"arm64", "aarch64"} else "x64"
        asset = f"layman-{system}-{arch}.zip"
        install_root = home / ".local" / "bin"
        notice_root = home / "data" / "layman" / "installation"
    install_root.mkdir(parents=True)
    installed = install_root / executable
    installed.write_bytes(b"old executable")
    archive = tmp_path / asset
    payload = b"not executable in Windows fixture" if windows else b"#!/bin/sh\nexit 0\n"
    if missing == "setup_failure":
        # A real harmless native Windows program: unsupported setup arguments
        # return nonzero. No model, configuration change or synthetic shell mock.
        payload = (Path(os.environ["SystemRoot"]) / "System32" / "where.exe").read_bytes()
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr(executable, payload)
        for name in NOTICES:
            if name != missing:
                package.writestr(name, f"fixture {name}\n")
        if missing != "THIRD_PARTY_LICENSES":
            package.writestr("THIRD_PARTY_LICENSES/fixture.txt", "fixture license\n")
    checksums = tmp_path / "SHA256SUMS.txt"
    checksums.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {asset}\n", encoding="utf-8")
    env = {**os.environ, "TEMP": str(temporary), "TMP": str(temporary), "LAYMAN_TEST_ARCHIVE": str(archive), "LAYMAN_TEST_CHECKSUMS": str(checksums)}
    if windows:
        env.update(LOCALAPPDATA=str(home), LAYMAN_TEST_INSTALLER=str(ROOT / "install.ps1"),
                   LAYMAN_TEST_SETUP_FAIL="1" if missing == "setup_failure" else "0")
        command = [shell, "-NoProfile", "-NonInteractive", "-Command", """
function Invoke-RestMethod { param($Headers,$Uri)
  [pscustomobject]@{ assets=@(
    [pscustomobject]@{name='layman-windows-x64.zip';browser_download_url='fixture-archive'},
    [pscustomobject]@{name='SHA256SUMS.txt';browser_download_url='fixture-checksums'}) }
}
function Invoke-WebRequest { param($Headers,$Uri,$OutFile)
  $source = if ($Uri -eq 'fixture-archive') { $env:LAYMAN_TEST_ARCHIVE } else { $env:LAYMAN_TEST_CHECKSUMS }
  Copy-Item -LiteralPath $source -Destination $OutFile
}
& $env:LAYMAN_TEST_INSTALLER -NoSetup:($env:LAYMAN_TEST_SETUP_FAIL -ne '1') -NoPathUpdate
"""]
    else:
        mocks = tmp_path / "mocks"
        mocks.mkdir()
        curl = mocks / "curl"
        curl.write_text("""#!/bin/sh
while [ "$#" -gt 0 ]; do
  case "$1" in -o) destination="$2"; shift 2;; *) url="$1"; shift;; esac
done
case "$url" in */SHA256SUMS.txt) cp "$LAYMAN_TEST_CHECKSUMS" "$destination";; *) cp "$LAYMAN_TEST_ARCHIVE" "$destination";; esac
""", encoding="utf-8")
        curl.chmod(0o755)
        env.update(HOME=str(home), XDG_DATA_HOME=str(home / "data"), LAYMAN_VERSION="fixture", LAYMAN_MODE="plus", PATH=str(mocks) + os.pathsep + env["PATH"])
        command = [shell, str(ROOT / "install.sh")]
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30, check=False)
    if missing == "setup_failure":
        assert result.returncode != 0
        assert "Setup failed" in result.stdout + result.stderr
        assert "Restart Codex" not in result.stdout + result.stderr
        assert installed.read_bytes() == payload
        return
    if missing:
        assert result.returncode != 0
        assert missing in result.stdout + result.stderr
        assert installed.read_bytes() == b"old executable"
        return
    assert result.returncode == 0, result.stdout + result.stderr
    assert installed.read_bytes() == payload
    for name in NOTICES:
        assert (notice_root / name).read_text(encoding="utf-8") == f"fixture {name}\n"
    assert (notice_root / "THIRD_PARTY_LICENSES" / "fixture.txt").read_text() == "fixture license\n"
    # Reinstallation must merge into the dedicated directory, not nest it.
    repeat = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30, check=False)
    assert repeat.returncode == 0, repeat.stdout + repeat.stderr
    assert not (notice_root / "THIRD_PARTY_LICENSES" / "THIRD_PARTY_LICENSES").exists()
