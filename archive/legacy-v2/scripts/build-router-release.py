#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release" / "layman-router-v2.1-rc"
PACKAGE_OUT = OUT / "packages"
DIRECT_DEPENDENCIES = ["fastapi", "httpx", "jsonschema", "pydantic", "PyYAML", "tomlkit", "uvicorn"]
V1_SHA256 = "A9F1736B6754BD1A5E6BAAD4E53ABBB1F9F07742D7C82C55CA96F457FC7D1B84"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    if digest(ROOT / "dist" / "layman-skill-v1.zip") != V1_SHA256:
        raise SystemExit("v1 artifact changed; refusing to build v2.1")
    if OUT.exists():
        shutil.rmtree(OUT)
    PACKAGE_OUT.mkdir(parents=True)
    build_environment = os.environ.copy()
    build_environment["SOURCE_DATE_EPOCH"] = "1784160000"
    subprocess.run(
        [sys.executable, "-m", "build", str(ROOT / "services" / "layman-router"), "--outdir", str(PACKAGE_OUT)],
        check=True,
        env=build_environment,
    )

    plugin = ROOT / "plugins" / "layman-router"
    plugin_zip = PACKAGE_OUT / "layman-router-codex-plugin-0.3.0.zip"
    with zipfile.ZipFile(plugin_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(plugin.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, Path("layman-router") / path.relative_to(plugin))

    sbom = {
        "format": "layman-router-simple-sbom-v1",
        "product": {"name": "layman-router", "version": "0.3.0"},
        "components": [
            {"name": name, "version": importlib.metadata.version(name), "relationship": "direct-runtime-dependency"}
            for name in DIRECT_DEPENDENCIES
        ],
    }
    (OUT / "sbom.json").write_text(json.dumps(sbom, indent=2), encoding="utf-8")
    shutil.copy2(ROOT / "RELEASE_NOTES_v2.1.md", OUT / "RELEASE_NOTES.md")
    shutil.copy2(ROOT / "docs" / "INSTALL.md", OUT / "INSTALL.md")
    shutil.copy2(ROOT / "docs" / "RECOVERY.md", OUT / "RECOVERY.md")
    shutil.copy2(ROOT / "docs" / "SECURITY.md", OUT / "SECURITY.md")
    shutil.copy2(ROOT / "docs" / "BENCHMARKS.md", OUT / "BENCHMARKS.md")
    shutil.copy2(ROOT / "services" / "layman-router" / "requirements.lock", OUT / "requirements.lock")
    artifacts = sorted(path for path in OUT.rglob("*") if path.is_file())
    checksums = {str(path.relative_to(OUT)).replace("\\", "/"): digest(path) for path in artifacts}
    (OUT / "SHA256SUMS.json").write_text(json.dumps(checksums, indent=2), encoding="utf-8")
    print(json.dumps({"release": str(OUT), "artifacts": checksums}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
