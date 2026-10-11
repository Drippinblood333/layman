from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
NOTICES = ("BUILD.json", "bundle-audit.json", "runtime-dependencies.json", "standalone-components.json", "THIRD_PARTY_NOTICES.md")


def shell_path(path: Path) -> str:
    value = path.resolve().as_posix()
    return f"/{value[0].lower()}{value[2:]}" if os.name == "nt" else value


@pytest.mark.parametrize("failure", ["none", "install", "notice_commit", "commit"])
def test_posix_installer_preserves_old_pair_on_failure(tmp_path, failure):
    shell = shutil.which("sh") if os.name != "nt" else "C:/Program Files/Git/bin/bash.exe"
    if not shell or not Path(shell).is_file():
        pytest.skip("POSIX shell unavailable")
    home = tmp_path / "home"
    binary = home / ".local/bin/layman"
    notices = home / "data/layman/installation"
    binary.parent.mkdir(parents=True)
    notices.mkdir(parents=True)
    binary.write_bytes(b"old executable")
    for name in NOTICES:
        (notices / name).write_text("old " + name, encoding="utf-8")
    (notices / "THIRD_PARTY_LICENSES").mkdir()
    (notices / "THIRD_PARTY_LICENSES/fixture.txt").write_text("old license", encoding="utf-8")
    (notices / "user-file.txt").write_text("keep user file", encoding="utf-8")
    payload = b"#!/bin/sh\nexit 0\n"
    archive = tmp_path / "layman-linux-x64.zip"
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("layman", payload)
        for name in NOTICES:
            package.writestr(name, "new " + name)
        package.writestr("THIRD_PARTY_LICENSES/fixture.txt", "new license")
    checksums = tmp_path / "SHA256SUMS.txt"
    checksums.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n", encoding="utf-8")
    mocks = tmp_path / "mocks"
    mocks.mkdir()
    scripts = {
        "uname": '#!/bin/sh\ncase "$1" in -s) echo Linux;; -m) echo x86_64;; esac\n',
        "curl": '''#!/bin/sh
while [ "$#" -gt 0 ]; do
  case "$1" in -o) destination="$2"; shift 2;; *) url="$1"; shift;; esac
done
case "$url" in */SHA256SUMS.txt) cp "$LAYMAN_TEST_CHECKSUMS" "$destination";; *) cp "$LAYMAN_TEST_ARCHIVE" "$destination";; esac
''',
        "install": '''#!/bin/sh
if [ "$LAYMAN_TEST_FAILURE" = install ]; then echo 'Injected install failure' >&2; exit 1; fi
exec "$LAYMAN_REAL_INSTALL" "$@"
''',
        "mv": '''#!/bin/sh
if [ "$LAYMAN_TEST_FAILURE" = commit ]; then
  case "$1" in */.layman-stage.*) echo 'Injected commit failure' >&2; exit 1;; esac
fi
if [ "$LAYMAN_TEST_FAILURE" = notice_commit ]; then
  case "$1" in */.installation-stage.*) echo 'Injected notice_commit failure' >&2; exit 1;; esac
fi
exec "$LAYMAN_REAL_MV" "$@"
''',
    }
    for name, text in scripts.items():
        path = mocks / name
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)
    real_tools = subprocess.run(
        [shell, "-c", "command -v install; command -v mv"], capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert len(real_tools) == 2
    env = {**os.environ, "HOME": shell_path(home), "XDG_DATA_HOME": shell_path(home / "data"),
           "LAYMAN_VERSION": "fixture", "LAYMAN_TEST_FAILURE": failure,
           "LAYMAN_TEST_ARCHIVE": shell_path(archive), "LAYMAN_TEST_CHECKSUMS": shell_path(checksums),
           "LAYMAN_TEST_MOCKS": shell_path(mocks), "LAYMAN_TEST_INSTALLER": shell_path(ROOT / "install.sh"),
           "LAYMAN_REAL_INSTALL": real_tools[0], "LAYMAN_REAL_MV": real_tools[1]}
    result = subprocess.run(
        [shell, "-c", 'export PATH="$LAYMAN_TEST_MOCKS:$PATH"; exec sh "$LAYMAN_TEST_INSTALLER"'],
        env=env, capture_output=True, text=True, timeout=30, check=False,
    )
    assert (notices / "user-file.txt").read_text() == "keep user file"
    if failure == "none":
        assert result.returncode == 0, result.stdout + result.stderr
        assert binary.read_bytes() == payload
        expected = "new "
    else:
        assert result.returncode != 0, result.stdout + result.stderr
        assert f"Injected {failure} failure" in result.stderr
        assert binary.read_bytes() == b"old executable"
        assert "Installed Layman" not in result.stdout
        expected = "old "
    for name in NOTICES:
        assert (notices / name).read_text() == expected + name
    assert (notices / "THIRD_PARTY_LICENSES/fixture.txt").read_text() == expected + "license"
    assert not list(binary.parent.glob(".layman-stage.*"))
    assert not list(notices.parent.glob(".installation-*"))
