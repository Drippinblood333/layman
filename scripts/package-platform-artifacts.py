#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ROOT / "release" / "layman-v1.0.0" / "platforms"


def main() -> int:
    for directory in sorted(path for path in PLATFORMS.iterdir() if path.is_dir()):
        shutil.make_archive(str(PLATFORMS / directory.name), "zip", directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
