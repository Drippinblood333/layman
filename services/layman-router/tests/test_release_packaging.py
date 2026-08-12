from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLATFORMS = {
    "layman-windows-x64": ("windows-x64", "layman.exe"),
    "layman-macos-x64": ("macos-x64", "layman"),
    "layman-macos-arm64": ("macos-arm64", "layman"),
    "layman-linux-x64": ("linux-x64", "layman"),
    "layman-linux-arm64": ("linux-arm64", "layman"),
}


def run_script(name: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / name), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_platform_artifacts_are_packaged_as_root_level_release_zips(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    output = tmp_path / "release"
    for artifact, (platform, executable) in PLATFORMS.items():
        directory = artifacts / artifact
        directory.mkdir(parents=True)
        (directory / executable).write_bytes(b"binary")
        (directory / "BUILD.json").write_text(
            json.dumps({"platform": platform, "executable": executable}), encoding="utf-8"
        )

    result = run_script(
        "package-platform-artifacts.py", "--artifacts", str(artifacts), "--output", str(output)
    )
    assert result.returncode == 0, result.stderr
    for artifact, (_, executable) in PLATFORMS.items():
        archive = output / f"{artifact}.zip"
        assert archive.is_file()
        with zipfile.ZipFile(archive) as package:
            assert {executable, "BUILD.json"} <= set(package.namelist())


def test_staged_release_assets_are_flat_and_match_checksums(tmp_path: Path):
    release = tmp_path / "release"
    output = tmp_path / "public-assets"
    (release / "python").mkdir(parents=True)
    (release / "legacy").mkdir()
    files = {
        release / "layman-codex-plugin-1.0.0.zip": b"plugin",
        release / "python" / "layman_codex-1.0.0-py3-none-any.whl": b"wheel",
        release / "python" / "layman_codex-1.0.0.tar.gz": b"sdist",
        release / "legacy" / "layman-skill-v1.zip": b"legacy",
        release / "legacy" / "layman-skill-v1.zip.sha256": b"legacy-checksum",
        release / "sbom.cdx.json": b"{}",
        release / "requirements.lock": b"dependency==1.0 \\",
        release / "RELEASE_NOTES.md": b"notes",
        release / "README.md": b"readme",
        release / "README.zh-CN.md": b"readme-zh",
        release / "LICENSE": b"license",
        release / "THIRD_PARTY_NOTICES.md": b"notices",
        release / "SECURITY.md": b"security",
    }
    for path, content in files.items():
        path.write_bytes(content)
    with zipfile.ZipFile(release / "layman-windows-x64.zip", "w") as package:
        package.writestr("layman.exe", b"binary")
        package.writestr("BUILD.json", b"{}")

    result = run_script(
        "stage-release-assets.py", "--release", str(release), "--output", str(output)
    )
    assert result.returncode == 0, result.stderr
    checksums = json.loads((output / "SHA256SUMS.json").read_text(encoding="utf-8"))
    assert "layman-windows-x64.zip" in checksums
    assert all("/" not in name and "\\" not in name for name in checksums)
    for name, expected in checksums.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest().upper() == expected

    strict = run_script(
        "stage-release-assets.py",
        "--release",
        str(release),
        "--output",
        str(tmp_path / "strict-assets"),
        "--require-all-platforms",
    )
    assert strict.returncode != 0
    assert "required platform archive not found" in strict.stderr

    existing_external = tmp_path / "existing-output"
    existing_external.mkdir()
    marker = existing_external / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    unsafe = run_script(
        "stage-release-assets.py",
        "--release",
        str(release),
        "--output",
        str(existing_external),
    )
    assert unsafe.returncode != 0
    assert "refusing unsafe staging cleanup target" in unsafe.stderr
    assert marker.read_text(encoding="utf-8") == "keep"
