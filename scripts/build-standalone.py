#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
from pathlib import Path

import PyInstaller.__main__


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"


def platform_id() -> str:
    system = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), platform.system().lower())
    machine = platform.machine().lower()
    architecture = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    return f"{system}-{architecture}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "release" / f"layman-v{VERSION}")
    args = parser.parse_args()
    target = args.output.resolve() / platform_id()
    work = ROOT / "build" / "pyinstaller" / platform_id()
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    work.mkdir(parents=True, exist_ok=True)
    separator = os.pathsep
    PyInstaller.__main__.run([
        str(ROOT / "scripts" / "standalone_entry.py"),
        "--name", "layman", "--onefile", "--clean", "--noconfirm",
        "--collect-all", "layman_router",
        "--add-data", f"{ROOT / '.agents' / 'plugins' / 'marketplace.json'}{separator}layman-bundle/.agents/plugins",
        "--add-data", f"{ROOT / 'plugins' / 'layman'}{separator}layman-bundle/plugins/layman",
        "--distpath", str(target), "--workpath", str(work / "work"), "--specpath", str(work),
    ])
    executable = target / ("layman.exe" if platform.system() == "Windows" else "layman")
    if not executable.exists():
        raise SystemExit(f"standalone executable was not created: {executable}")
    metadata = {"product": "Layman", "version": VERSION, "platform": platform_id(), "executable": executable.name}
    (target / "BUILD.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({**metadata, "path": str(executable)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
