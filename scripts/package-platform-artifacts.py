#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from release_archives import write_platform_archive
from runtime_inventory import BUNDLE_AUDIT_NAME, STANDALONE_MANIFEST_NAME


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "layman-windows-x64": ("windows-x64", "layman.exe"),
    "layman-macos-x64": ("macos-x64", "layman"),
    "layman-macos-arm64": ("macos-arm64", "layman"),
    "layman-linux-x64": ("linux-x64", "layman"),
    "layman-linux-arm64": ("linux-arm64", "layman"),
}
MANIFEST_NAME = "runtime-dependencies.json"
COMPLIANCE_FILES = {
    BUNDLE_AUDIT_NAME,
    "BUILD.json",
    "THIRD_PARTY_NOTICES.md",
    MANIFEST_NAME,
    STANDALONE_MANIFEST_NAME,
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
    reference_manifest: bytes | None = None
    for artifact_name, (platform, executable_name) in EXPECTED.items():
        directory = artifacts / artifact_name
        executable = directory / executable_name
        metadata_path = directory / "BUILD.json"
        if not executable.is_file() or any(
            not (directory / filename).is_file() for filename in COMPLIANCE_FILES
        ):
            raise SystemExit(f"incomplete platform artifact: {artifact_name}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("platform") != platform or metadata.get("executable") != executable_name:
            raise SystemExit(f"platform metadata mismatch: {artifact_name}")
        manifest_content = (directory / MANIFEST_NAME).read_bytes()
        inventory = metadata.get("runtime_dependencies")
        if not isinstance(inventory, dict) or inventory.get("path") != MANIFEST_NAME:
            raise SystemExit(f"platform runtime manifest identity missing: {artifact_name}")
        if inventory.get("sha256") != hashlib.sha256(manifest_content).hexdigest():
            raise SystemExit(f"platform runtime manifest digest mismatch: {artifact_name}")
        if not inventory.get("requirements_lock_sha256"):
            raise SystemExit(f"platform requirements lock digest missing: {artifact_name}")
        standalone_content = (directory / STANDALONE_MANIFEST_NAME).read_bytes()
        standalone = metadata.get("standalone_components")
        if not isinstance(standalone, dict) or standalone.get("path") != STANDALONE_MANIFEST_NAME:
            raise SystemExit(f"platform standalone component identity missing: {artifact_name}")
        if standalone.get("sha256") != hashlib.sha256(standalone_content).hexdigest():
            raise SystemExit(f"platform standalone manifest digest mismatch: {artifact_name}")
        audit_content = (directory / BUNDLE_AUDIT_NAME).read_bytes()
        audit = metadata.get("bundle_audit")
        if not isinstance(audit, dict) or audit.get("path") != BUNDLE_AUDIT_NAME:
            raise SystemExit(f"platform bundle audit identity missing: {artifact_name}")
        if audit.get("sha256") != hashlib.sha256(audit_content).hexdigest():
            raise SystemExit(f"platform bundle audit digest mismatch: {artifact_name}")
        if audit.get("executable_sha256") != hashlib.sha256(executable.read_bytes()).hexdigest():
            raise SystemExit(f"platform executable digest mismatch: {artifact_name}")
        if reference_manifest is None:
            reference_manifest = manifest_content
        elif manifest_content != reference_manifest:
            raise SystemExit(f"platform runtime manifests differ: {artifact_name}")
        archive = output / f"{artifact_name}.zip"
        archive.unlink(missing_ok=True)
        write_platform_archive(
            directory,
            archive,
            executable,
            posix_executable=platform.startswith(("linux-", "macos-")),
        )
        with zipfile.ZipFile(archive) as package:
            names = set(package.namelist())
        if executable_name not in names or not COMPLIANCE_FILES <= names:
            raise SystemExit(f"platform archive has an invalid root layout: {archive}")
        archives.append(str(archive))
    print(json.dumps({"platform_archives": archives}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
