#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "layman-windows-x64": ("windows-x64", "layman.exe"),
    "layman-macos-x64": ("macos-x64", "layman"),
    "layman-macos-arm64": ("macos-arm64", "layman"),
    "layman-linux-x64": ("linux-x64", "layman"),
    "layman-linux-arm64": ("linux-arm64", "layman"),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=ROOT / "build" / "platform-artifacts")
    parser.add_argument("--output", type=Path, default=ROOT / "release" / "layman-v1.0.0")
    args = parser.parse_args()
    artifacts = args.artifacts.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    found = {path.name for path in artifacts.iterdir() if path.is_dir()} if artifacts.is_dir() else set()
    missing = sorted(set(EXPECTED) - found)
    unexpected = sorted(found - set(EXPECTED))
    if missing or unexpected:
        raise SystemExit(f"platform artifact directories mismatch: missing={missing}, unexpected={unexpected}")
    archives = []
    for artifact_name, (platform, executable_name) in EXPECTED.items():
        directory = artifacts / artifact_name
        executable = directory / executable_name
        metadata_path = directory / "BUILD.json"
        if not executable.is_file() or not metadata_path.is_file():
            raise SystemExit(f"incomplete platform artifact: {artifact_name}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("platform") != platform or metadata.get("executable") != executable_name:
            raise SystemExit(f"platform metadata mismatch: {artifact_name}")
        archive = output / f"{artifact_name}.zip"
        archive.unlink(missing_ok=True)
        shutil.make_archive(str(archive.with_suffix("")), "zip", directory)
        with zipfile.ZipFile(archive) as package:
            names = set(package.namelist())
        if executable_name not in names or "BUILD.json" not in names:
            raise SystemExit(f"platform archive has an invalid root layout: {archive}")
        archives.append(str(archive))
    print(json.dumps({"platform_archives": archives}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
