#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
PLATFORMS = {
    "windows-x64": "layman.exe",
    "macos-x64": "layman",
    "macos-arm64": "layman",
    "linux-x64": "layman",
    "linux-arm64": "layman",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def one_match(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one match for {pattern}, found {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, default=ROOT / "release" / f"layman-v{VERSION}")
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "release-assets")
    parser.add_argument("--require-all-platforms", action="store_true")
    args = parser.parse_args()
    release = args.release.resolve()
    output = args.output.resolve()
    if not release.is_dir():
        raise SystemExit(f"release directory not found: {release}")
    if output.exists():
        build_root = (ROOT / "build").resolve()
        if build_root not in output.parents:
            raise SystemExit(f"refusing unsafe staging cleanup target: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    sources = [
        release / f"layman-codex-plugin-{VERSION}.zip",
        one_match(release, f"python/layman_codex-{VERSION}-*.whl"),
        one_match(release, f"python/layman_codex-{VERSION}.tar.gz"),
        release / "legacy" / "layman-skill-v1.zip",
        release / "legacy" / "layman-skill-v1.zip.sha256",
        release / "sbom.cdx.json",
        release / "RELEASE_NOTES.md",
        release / "README.md",
        release / "README.zh-CN.md",
        release / "LICENSE",
        release / "THIRD_PARTY_NOTICES.md",
        release / "SECURITY.md",
    ]
    available_platforms = []
    for platform, executable in PLATFORMS.items():
        archive = release / f"layman-{platform}.zip"
        if not archive.is_file():
            if args.require_all_platforms:
                raise SystemExit(f"required platform archive not found: {archive.name}")
            continue
        with zipfile.ZipFile(archive) as package:
            names = set(package.namelist())
        if executable not in names or "BUILD.json" not in names:
            raise SystemExit(f"platform archive has an invalid root layout: {archive.name}")
        sources.append(archive)
        available_platforms.append(platform)
    if not available_platforms:
        raise SystemExit("no platform archives were found")

    destinations: dict[str, Path] = {}
    for source in sources:
        if not source.is_file():
            raise SystemExit(f"required release asset not found: {source}")
        if source.name in destinations:
            raise SystemExit(f"duplicate public release asset name: {source.name}")
        destination = output / source.name
        shutil.copy2(source, destination)
        destinations[source.name] = destination

    checksums = {name: digest(path) for name, path in sorted(destinations.items())}
    (output / "SHA256SUMS.json").write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")
    lines = [f"{value}  {name}" for name, value in checksums.items()]
    (output / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"assets": sorted(checksums), "platforms": available_platforms}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
