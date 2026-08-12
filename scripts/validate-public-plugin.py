#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "layman"


def main() -> int:
    manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    if manifest.get("name") != "layman":
        failures.append("plugin name must be layman")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(manifest.get("version", ""))):
        failures.append("plugin version must be strict semver")
    for field in ("description", "author", "interface", "skills", "mcpServers"):
        if not manifest.get(field):
            failures.append(f"missing plugin field: {field}")
    for skill in ("layman", "layman-auto", "layman-router", "layman-status"):
        path = PLUGIN / "skills" / skill / "SKILL.md"
        if not path.exists() or not path.read_text(encoding="utf-8").startswith("---\n"):
            failures.append(f"invalid skill: {skill}")
    for path in PLUGIN.rglob("*"):
        if path.is_file() and "[TODO" in path.read_text(encoding="utf-8", errors="ignore"):
            failures.append(f"TODO placeholder in {path.relative_to(ROOT)}")
    mcp_path = PLUGIN / ".mcp.json"
    if not mcp_path.exists() or "layman" not in json.loads(mcp_path.read_text(encoding="utf-8")).get("mcpServers", {}):
        failures.append("Layman MCP server config is missing")
    for installer in (ROOT / "install.ps1", ROOT / "install.sh"):
        content = installer.read_text(encoding="utf-8")
        if "SHA256SUMS.txt" not in content or "SHA-256 verification failed" not in content:
            failures.append(f"installer does not enforce release checksum verification: {installer.name}")
    if "SHA256SUMS.txt" not in (ROOT / "scripts" / "build-release.py").read_text(encoding="utf-8"):
        failures.append("release builder does not create SHA256SUMS.txt")
    if failures:
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    if not (ROOT / "THIRD_PARTY_NOTICES.md").exists() or not (ROOT / "docs" / "ARCHITECTURE.md").exists():
        print("- architecture and third-party provenance files are required")
        return 1
    print("Layman 1.0 plugin manifest, MCP server and all skills are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
