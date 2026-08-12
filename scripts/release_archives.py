from __future__ import annotations

import stat
import zipfile
from pathlib import Path


def write_platform_archive(
    directory: Path,
    archive: Path,
    executable: Path,
    *,
    posix_executable: bool,
) -> None:
    """Create a portable ZIP with deterministic Unix permission metadata."""

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for source in sorted(path for path in directory.rglob("*") if path.is_file()):
            member = source.relative_to(directory).as_posix()
            package.write(source, member)
            info = package.getinfo(member)
            permissions = 0o755 if posix_executable and source == executable else 0o644
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | permissions) << 16
