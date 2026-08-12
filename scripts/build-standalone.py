#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
from pathlib import Path

import PyInstaller.__main__

from runtime_inventory import (
    BUNDLE_AUDIT_NAME,
    MANIFEST_NAME,
    PYINSTALLER_VERSION,
    STANDALONE_MANIFEST_NAME,
    build_runtime_manifest,
    digest_bytes,
    validate_embedded_distributions,
    write_json,
    write_runtime_license_bundle,
    write_standalone_component_bundle,
)


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
        "--exclude-module", "setuptools",
        "--exclude-module", "packaging",
        "--exclude-module", "_distutils_hack",
        "--exclude-module", "pkg_resources",
        "--add-data", f"{ROOT / '.agents' / 'plugins' / 'marketplace.json'}{separator}layman-bundle/.agents/plugins",
        "--add-data", f"{ROOT / 'plugins' / 'layman'}{separator}layman-bundle/plugins/layman",
        "--distpath", str(target), "--workpath", str(work / "work"), "--specpath", str(work),
    ])
    executable = target / ("layman.exe" if platform.system() == "Windows" else "layman")
    if not executable.exists():
        raise SystemExit(f"standalone executable was not created: {executable}")
    lock_path = ROOT / "services" / "layman-router" / "requirements.lock"
    manifest_path = target / MANIFEST_NAME
    manifest = build_runtime_manifest(lock_path, VERSION)
    write_json(manifest_path, manifest)
    expected_distributions = {
        dependency["name"]: dependency["version"]
        for dependency in manifest["dependencies"]
    }
    expected_distributions.update(
        {"layman-codex": VERSION, "pyinstaller": PYINSTALLER_VERSION}
    )
    bundle_audit = validate_embedded_distributions(
        work / "work" / "layman" / "Analysis-00.toc",
        executable,
        expected_distributions,
    )
    bundle_audit_path = target / BUNDLE_AUDIT_NAME
    write_json(bundle_audit_path, bundle_audit)
    write_runtime_license_bundle(manifest, target)
    standalone_manifest = write_standalone_component_bundle(target)
    standalone_manifest_path = target / STANDALONE_MANIFEST_NAME
    shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", target / "THIRD_PARTY_NOTICES.md")
    metadata = {
        "product": "Layman",
        "version": VERSION,
        "platform": platform_id(),
        "executable": executable.name,
        "runtime_dependencies": {
            "path": MANIFEST_NAME,
            "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "requirements_lock_sha256": manifest["lock"]["sha256"],
        },
        "standalone_components": {
            "path": STANDALONE_MANIFEST_NAME,
            "sha256": digest_bytes(standalone_manifest_path.read_bytes()),
            "components": [component["name"] for component in standalone_manifest["components"]],
            "embedded_python_distributions": [
                distribution["name"] for distribution in bundle_audit["distributions"]
            ],
        },
        "bundle_audit": {
            "path": BUNDLE_AUDIT_NAME,
            "sha256": digest_bytes(bundle_audit_path.read_bytes()),
            "executable_sha256": bundle_audit["executable_sha256"],
        },
    }
    (target / "BUILD.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({**metadata, "path": str(executable)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
