#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def expected_bundle() -> dict[str, str]:
    expected = {
        ".agents/plugins/marketplace.json": digest(ROOT / ".agents" / "plugins" / "marketplace.json")
    }
    plugin = ROOT / "plugins" / "layman"
    expected.update(
        {
            (Path("plugins") / "layman" / path.relative_to(plugin)).as_posix(): digest(path)
            for path in sorted(plugin.rglob("*"))
            if path.is_file()
        }
    )
    return expected


def environment_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(command: list[str], *, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, env=environment, capture_output=True, text=True, check=True)


def smoke(artifact: Path, expected: dict[str, str]) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="layman-python-package-") as temporary:
        root = Path(temporary)
        environment_path = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment_path)
        python = environment_python(environment_path)
        environment = os.environ.copy()
        environment["LAYMAN_HOME"] = str(root / "layman-home")
        environment["LAYMAN_ROUTER_DATABASE_PATH"] = str(root / "layman-home" / "usage.sqlite3")
        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                str(artifact.resolve()),
            ],
            environment=environment,
        )
        inspection = run(
            [
                str(python),
                "-c",
                (
                    "import hashlib,json;"
                    "from pathlib import Path;"
                    "from layman_router.lifecycle import _bundle_root;"
                    "root=_bundle_root();"
                    "print(json.dumps({p.relative_to(root).as_posix():"
                    "hashlib.sha256(p.read_bytes()).hexdigest().upper() "
                    "for p in sorted(root.rglob('*')) if p.is_file()}))"
                ),
            ],
            environment=environment,
        )
        actual = json.loads(inspection.stdout)
        if actual != expected:
            missing = sorted(set(expected) - set(actual))
            unexpected = sorted(set(actual) - set(expected))
            changed = sorted(name for name in set(actual) & set(expected) if actual[name] != expected[name])
            raise RuntimeError(
                f"bundled plugin mismatch for {artifact.name}: "
                f"missing={missing}, unexpected={unexpected}, changed={changed}"
            )
        run([str(python), "-m", "layman_router.cli", "--help"], environment=environment)
        doctor = run([str(python), "-m", "layman_router.cli", "doctor"], environment=environment)
        doctor_result = json.loads(doctor.stdout)
        if not doctor_result.get("listen_is_loopback") or not doctor_result.get("database_parent_writable"):
            raise RuntimeError(f"package doctor failed for {artifact.name}: {doctor_result}")
        return {"artifact": artifact.name, "bundle_files": len(actual), "doctor": doctor_result}


def one_artifact(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {pattern} in {directory}, found {[path.name for path in matches]}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Install and smoke-test the release wheel and source distribution")
    parser.add_argument(
        "--packages",
        type=Path,
        default=ROOT / "release" / f"layman-v{VERSION}" / "python",
    )
    args = parser.parse_args()
    packages = args.packages.resolve()
    artifacts = [
        one_artifact(packages, "layman_codex-*.whl"),
        one_artifact(packages, "layman_codex-*.tar.gz"),
    ]
    expected = expected_bundle()
    results = [smoke(artifact, expected) for artifact in artifacts]
    print(json.dumps({"status": "passed", "packages": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
