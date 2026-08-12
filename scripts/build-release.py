#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from runtime_inventory import (
    MANIFEST_NAME,
    PLATFORM_ARCHIVE_PATTERN,
    build_runtime_manifest,
    build_sbom,
    validate_release_runtime,
    write_json,
)
from release_archives import write_platform_archive


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
V1_SHA256 = "A9F1736B6754BD1A5E6BAAD4E53ABBB1F9F07742D7C82C55CA96F457FC7D1B84"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    if digest(ROOT / "dist" / "layman-skill-v1.zip") != V1_SHA256:
        raise SystemExit("legacy v1 artifact changed")
    output = ROOT / "release" / f"layman-v{VERSION}"
    output.mkdir(parents=True, exist_ok=True)
    python_packages = output / "python"
    python_packages.mkdir(exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "build", str(ROOT / "services" / "layman-router"), "--outdir", str(python_packages)],
        check=True,
    )
    plugin_zip = output / f"layman-codex-plugin-{VERSION}.zip"
    with zipfile.ZipFile(plugin_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted((ROOT / "plugins" / "layman").rglob("*")):
            if path.is_file():
                archive.write(path, Path("layman") / path.relative_to(ROOT / "plugins" / "layman"))
        archive.write(ROOT / "LICENSE", Path("layman") / "LICENSE")
        archive.write(ROOT / "THIRD_PARTY_NOTICES.md", Path("layman") / "THIRD_PARTY_NOTICES.md")
    release_docs = output / "docs"
    release_docs.mkdir(exist_ok=True)
    for source, destination in (
        (ROOT / "README.md", output / "README.md"),
        (ROOT / "README.zh-CN.md", output / "README.zh-CN.md"),
        (ROOT / "LICENSE", output / "LICENSE"),
        (ROOT / "THIRD_PARTY_NOTICES.md", output / "THIRD_PARTY_NOTICES.md"),
        (ROOT / "SECURITY.md", output / "SECURITY.md"),
        (ROOT / "RELEASE_NOTES_v1.0.0.md", output / "RELEASE_NOTES.md"),
        (ROOT / "docs" / "ARCHITECTURE.md", release_docs / "ARCHITECTURE.md"),
        (ROOT / "docs" / "INSTALL.md", release_docs / "INSTALL.md"),
        (ROOT / "docs" / "RECOVERY.md", release_docs / "RECOVERY.md"),
        (ROOT / "docs" / "BENCHMARKS.md", release_docs / "BENCHMARKS.md"),
    ):
        shutil.copy2(source, destination)
    legacy = output / "legacy"
    legacy.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "dist" / "layman-skill-v1.zip", legacy / "layman-skill-v1.zip")
    shutil.copy2(ROOT / "dist" / "layman-skill-v1.zip.sha256", legacy / "layman-skill-v1.zip.sha256")
    lock_path = ROOT / "services" / "layman-router" / "requirements.lock"
    shutil.copy2(lock_path, output / "requirements.lock")
    for directory in sorted(path for path in output.iterdir() if path.is_dir() and path.name in {
        "windows-x64", "windows-arm64", "macos-x64", "macos-arm64", "linux-x64", "linux-arm64"
    }):
        archive = output / f"layman-{directory.name}.zip"
        archive.unlink(missing_ok=True)
        executable = directory / ("layman.exe" if directory.name.startswith("windows-") else "layman")
        if not executable.is_file():
            raise SystemExit(f"standalone executable is missing: {executable}")
        write_platform_archive(
            directory,
            archive,
            executable,
            posix_executable=not directory.name.startswith("windows-"),
        )
    manifest_path = output / MANIFEST_NAME
    sbom_path = output / "sbom.cdx.json"
    manifest = build_runtime_manifest(lock_path, VERSION)
    write_json(manifest_path, manifest)
    write_json(sbom_path, build_sbom(manifest))
    platform_archives = sorted(
        path
        for path in output.glob("*.zip")
        if PLATFORM_ARCHIVE_PATTERN.fullmatch(path.name)
    )
    validate_release_runtime(lock_path, manifest_path, sbom_path, platform_archives)
    checksum_names = {"SHA256SUMS.json", "SHA256SUMS.txt"}
    artifacts = sorted(path for path in output.rglob("*") if path.is_file() and path.name not in checksum_names)
    checksums = {str(path.relative_to(output)).replace("\\", "/"): digest(path) for path in artifacts}
    (output / "SHA256SUMS.json").write_text(json.dumps(checksums, indent=2), encoding="utf-8")
    checksum_lines = [f"{value}  {name}" for name, value in checksums.items()]
    (output / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(json.dumps({"release": str(output), "artifacts": checksums}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
