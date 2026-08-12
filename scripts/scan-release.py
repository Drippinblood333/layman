#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "OpenAI-style secret": re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "long bearer token": re.compile(rb"Bearer\s+[A-Za-z0-9._-]{32,}", re.IGNORECASE),
}
TEXT_EXTENSIONS = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".ps1", ".sh", ".txt"}


def inspect(name: str, content: bytes, failures: list[str]) -> None:
    for label, pattern in PATTERNS.items():
        if pattern.search(content):
            failures.append(f"{label} found in {name}")


def main(argv: list[str] | None = None) -> int:
    targets = [Path(value).resolve() for value in (argv or sys.argv[1:])] or [ROOT]
    failures: list[str] = []
    for target in targets:
        paths = target.rglob("*") if target.is_dir() else [target]
        for path in paths:
            if not path.is_file() or any(part in {".git", ".venv", "build"} for part in path.parts):
                continue
            if path.suffix.lower() == ".zip":
                with zipfile.ZipFile(path) as archive:
                    for member in archive.infolist():
                        if not member.is_dir() and Path(member.filename).suffix.lower() in TEXT_EXTENSIONS:
                            inspect(f"{path}:{member.filename}", archive.read(member), failures)
            elif path.suffix.lower() in TEXT_EXTENSIONS:
                inspect(str(path), path.read_bytes(), failures)
    if failures:
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    print("Release secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
