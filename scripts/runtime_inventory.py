#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import zipfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
MANIFEST_NAME = "runtime-dependencies.json"
STANDALONE_MANIFEST_NAME = "standalone-components.json"
BUNDLE_AUDIT_NAME = "bundle-audit.json"
LICENSE_ROOT = "THIRD_PARTY_LICENSES"
PYINSTALLER_VERSION = "6.22.0"
PYINSTALLER_HOOKS_CONTRIB_VERSION = "2026.6"
CPYTHON_VERSION = "3.14.3"
CPYTHON_LICENSE_SHA256 = "939d8e9fa591cbaff0d51e777edb4c1002045d2600ce43a1ae28530cecfc5b88"
CPYTHON_SOURCE_LICENSE_URL_TEMPLATE = (
    "https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip#LICENSE.txt"
)
CPYTHON_LICENSE_MARKERS = (
    "PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2",
    "BEOPEN.COM LICENSE AGREEMENT FOR PYTHON 2.0",
    "CNRI LICENSE AGREEMENT FOR PYTHON 1.6.1",
    "CWI LICENSE AGREEMENT FOR PYTHON 0.9.0 THROUGH 1.2",
)
LOCK_PATTERN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)\s*\\$")
PLATFORM_ARCHIVE_PATTERN = re.compile(r"^layman-(?:windows|macos|linux)-[^/]+\.zip$")
SUPPORTED_SPDX_EXPRESSIONS = frozenset({"BSD-3-Clause", "MIT", "MPL-2.0", "PSF-2.0"})
APPROVED_RUNTIME_LICENSES = {
    ("annotated-doc", "0.0.5"): "MIT",
    ("annotated-types", "0.8.0"): "MIT",
    ("anyio", "4.14.2"): "MIT",
    ("attrs", "26.1.0"): "MIT",
    ("certifi", "2026.7.22"): "MPL-2.0",
    ("click", "8.4.2"): "BSD-3-Clause",
    ("colorama", "0.4.6"): "BSD-3-Clause",
    ("fastapi", "0.141.1"): "MIT",
    ("h11", "0.16.0"): "MIT",
    ("httpcore", "1.0.9"): "BSD-3-Clause",
    ("httpx", "0.28.1"): "BSD-3-Clause",
    ("idna", "3.18"): "BSD-3-Clause",
    ("jsonschema", "4.26.0"): "MIT",
    ("jsonschema-specifications", "2025.9.1"): "MIT",
    ("pydantic", "2.13.4"): "MIT",
    ("pydantic-core", "2.46.4"): "MIT",
    ("pyyaml", "6.0.3"): "MIT",
    ("referencing", "0.37.0"): "MIT",
    ("rpds-py", "2026.6.3"): "MIT",
    ("starlette", "1.6.0"): "BSD-3-Clause",
    ("tomlkit", "0.15.1"): "MIT",
    ("typing-extensions", "4.16.0"): "PSF-2.0",
    ("typing-inspection", "0.4.3"): "MIT",
    ("uvicorn", "0.52.1"): "BSD-3-Clause",
}
CLASSIFIER_LICENSES = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
}
LICENSE_OVERRIDES = {
    ("certifi", "2026.7.22"): {
        "expression": "MPL-2.0",
        "evidence": "curated-upstream-license",
        "url": "https://github.com/certifi/python-certifi/blob/f4bc676bc101fe2235846e37044e8c693d6cbaf4/LICENSE",
    },
    ("colorama", "0.4.6"): {
        "expression": "BSD-3-Clause",
        "evidence": "curated-upstream-license",
        "url": "https://github.com/tartley/colorama/blob/3de9f013df4b470069d03d250224062e8cf15c49/LICENSE.txt",
    },
    ("h11", "0.16.0"): {
        "expression": "MIT",
        "evidence": "curated-upstream-license",
        "url": "https://github.com/python-hyper/h11/blob/1c5b07581f058886c8bdd87adababd7d959dc7ca/LICENSE.txt",
    },
    ("httpx", "0.28.1"): {
        "expression": "BSD-3-Clause",
        "evidence": "curated-upstream-license",
        "url": "https://github.com/encode/httpx/blob/26d48e0634e6ee9cdc0533996db289ce4b430177/LICENSE.md",
    },
    ("pyyaml", "6.0.3"): {
        "expression": "MIT",
        "evidence": "curated-upstream-license",
        "url": "https://github.com/yaml/pyyaml/blob/49790e73684bebad1df05ef8d828fa12f685bffb/LICENSE",
    },
    ("tomlkit", "0.15.1"): {
        "expression": "MIT",
        "evidence": "curated-upstream-license",
        "url": "https://github.com/python-poetry/tomlkit/blob/1bd7e3bc5bcc957d359a6c4d8e420163f32ac009/LICENSE",
    },
}


def canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def validate_cpython_license(content: bytes) -> None:
    if digest_bytes(content) != CPYTHON_LICENSE_SHA256:
        raise RuntimeError("bundled CPython license differs from the reviewed source digest")
    text = content.decode("utf-8")
    missing = [marker for marker in CPYTHON_LICENSE_MARKERS if marker not in text]
    if missing:
        raise RuntimeError(
            f"bundled CPython license is incomplete; missing sections={missing}"
        )


def locked_dependencies(path: Path) -> list[tuple[str, str]]:
    dependencies: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = LOCK_PATTERN.match(line)
        if not match:
            continue
        name, version = canonical_name(match.group(1)), match.group(2)
        if name in dependencies:
            raise RuntimeError(f"duplicate locked dependency: {name}")
        dependencies[name] = version
    if not dependencies:
        raise RuntimeError(f"no hashed dependencies found in {path}")
    return sorted(dependencies.items())


def _analysis_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield from _analysis_strings(key)
            yield from _analysis_strings(item)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _analysis_strings(item)


def _normalized_path(path: Path | str) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def validate_embedded_distributions(
    analysis_path: Path,
    executable_path: Path,
    expected_distributions: Mapping[str, str],
    *,
    distributions: Iterable[importlib.metadata.Distribution] | None = None,
) -> dict[str, Any]:
    """Reject files embedded from undeclared Python distributions.

    PyInstaller's analysis file records the original path for every collected
    module, binary, and data file. Matching those paths against installed
    distribution RECORDs closes the gap between the reviewed runtime lock and
    the code that is actually frozen into the standalone executable.
    """

    try:
        analysis = ast.literal_eval(analysis_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError) as exc:
        raise RuntimeError(f"cannot read PyInstaller analysis: {analysis_path}") from exc

    embedded_sources: dict[str, str] = {}
    for value in _analysis_strings(analysis):
        source = Path(value)
        parts = {part.casefold() for part in source.parts}
        if not {"site-packages", "dist-packages"} & parts or not source.is_file():
            continue
        embedded_sources[_normalized_path(source)] = str(source)
    if not embedded_sources:
        raise RuntimeError("PyInstaller analysis contains no auditable site-packages files")

    owners: dict[str, set[tuple[str, str]]] = {
        path: set() for path in embedded_sources
    }
    installed = distributions if distributions is not None else importlib.metadata.distributions()
    installed_versions: dict[str, set[str]] = {}
    for distribution in installed:
        metadata_name = distribution.metadata.get("Name")
        if not metadata_name:
            continue
        name = canonical_name(str(metadata_name))
        version = str(distribution.version)
        installed_versions.setdefault(name, set()).add(version)
        for entry in distribution.files or ():
            located = _normalized_path(distribution.locate_file(entry))
            if located in owners:
                owners[located].add((name, version))

    unowned = sorted(
        Path(embedded_sources[path]).name for path, names in owners.items() if not names
    )
    ambiguous = sorted(
        Path(embedded_sources[path]).name for path, names in owners.items() if len(names) > 1
    )
    embedded = {owner for names in owners.values() for owner in names}
    expected = {
        canonical_name(name): str(version)
        for name, version in expected_distributions.items()
    }
    embedded_versions = {name: version for name, version in embedded}
    unexpected = sorted(set(embedded_versions) - set(expected))
    missing = sorted(set(expected) - set(embedded_versions))
    mismatched = sorted(
        name
        for name in set(expected) & set(embedded_versions)
        if embedded_versions[name] != expected[name]
    )
    duplicate_installs = sorted(
        name for name, versions in installed_versions.items() if len(versions) > 1
    )
    if unexpected or missing or mismatched or unowned or ambiguous or duplicate_installs:
        raise RuntimeError(
            "standalone contains unreviewed Python distribution files: "
            f"unexpected={unexpected}, missing={missing}, mismatched={mismatched}, "
            f"unowned={unowned}, ambiguous={ambiguous}, duplicate_installs={duplicate_installs}"
        )

    try:
        from PyInstaller.archive.readers import CArchiveReader

        executable_archive = CArchiveReader(str(executable_path))
        python_archive = executable_archive.open_embedded_archive("PYZ.pyz")
    except (ImportError, KeyError, OSError, ValueError) as exc:
        raise RuntimeError(f"cannot audit standalone executable: {executable_path}") from exc

    module_roots = {
        name.replace("\\", "/").split("/", 1)[0].split(".", 1)[0]
        for name in python_archive.toc
    }
    extension_suffixes = (".pyd", ".so", ".dylib")
    module_roots.update(
        name.replace("\\", "/").split("/", 1)[0].split(".", 1)[0]
        for name in executable_archive.toc
        if name.casefold().endswith(extension_suffixes)
    )
    packages = {
        package: {canonical_name(owner) for owner in package_owners}
        for package, package_owners in importlib.metadata.packages_distributions().items()
    }
    archive_distributions: set[str] = set()
    unexpected_roots: list[str] = []
    for root in sorted(module_roots):
        package_owners = packages.get(root, set())
        reviewed_owners = package_owners & set(expected)
        if reviewed_owners:
            archive_distributions.update(reviewed_owners)
        elif package_owners:
            unexpected_roots.append(root)
    if any(name.startswith("pyi") for name in executable_archive.toc):
        archive_distributions.add("pyinstaller")
    archive_missing = sorted(set(expected) - archive_distributions)
    if unexpected_roots or archive_missing:
        raise RuntimeError(
            "standalone executable distribution audit failed: "
            f"unexpected_roots={unexpected_roots}, missing={archive_missing}"
        )

    file_counts: dict[tuple[str, str], int] = {}
    for file_owners in owners.values():
        for owner in file_owners:
            file_counts[owner] = file_counts.get(owner, 0) + 1
    hooks_distribution = importlib.metadata.distribution("pyinstaller-hooks-contrib")
    if hooks_distribution.version != PYINSTALLER_HOOKS_CONTRIB_VERSION:
        raise RuntimeError(
            "PyInstaller hooks version is not release-pinned: "
            f"expected={PYINSTALLER_HOOKS_CONTRIB_VERSION} "
            f"installed={hooks_distribution.version}"
        )

    def names_digest(names: Iterable[str]) -> str:
        return digest_bytes("\n".join(sorted(names)).encode("utf-8"))

    return {
        "schema_version": 1,
        "analysis_sha256": digest(analysis_path),
        "executable_sha256": digest(executable_path),
        "distributions": [
            {
                "name": name,
                "version": expected[name],
                "file_count": file_counts[(name, expected[name])],
            }
            for name in sorted(expected)
        ],
        "archive": {
            "carchive_entries": len(executable_archive.toc),
            "carchive_names_sha256": names_digest(executable_archive.toc),
            "pyz_entries": len(python_archive.toc),
            "pyz_names_sha256": names_digest(python_archive.toc),
            "python_roots": len(module_roots),
            "python_roots_sha256": names_digest(module_roots),
            "distributions": sorted(archive_distributions),
        },
        "build_tools": [
            {"name": "CPython", "version": platform.python_version()},
            {"name": "PyInstaller", "version": PYINSTALLER_VERSION},
            {
                "name": "pyinstaller-hooks-contrib",
                "version": PYINSTALLER_HOOKS_CONTRIB_VERSION,
            },
        ],
        "unexpected": [],
        "unowned": [],
    }


def _metadata_values(package_metadata: Mapping[str, Any], key: str) -> list[str]:
    get_all = getattr(package_metadata, "get_all", None)
    if callable(get_all):
        return [str(value) for value in get_all(key, [])]
    value = package_metadata.get(key)
    if value is None:
        return []
    return [str(value)] if isinstance(value, str) else [str(item) for item in value]


def _metadata_url(name: str, version: str) -> str:
    return f"https://pypi.org/pypi/{name}/{version}/json"


def _source_url(package_metadata: Mapping[str, Any], name: str, version: str) -> str:
    candidates: dict[str, str] = {}
    for value in _metadata_values(package_metadata, "Project-URL"):
        if "," not in value:
            continue
        label, url = (part.strip() for part in value.split(",", 1))
        if url.startswith("https://"):
            candidates[label.casefold()] = url
    for label in ("source code", "source", "repository", "github", "homepage", "home"):
        if label in candidates:
            return candidates[label]
    homepage = package_metadata.get("Home-page")
    if isinstance(homepage, str) and homepage.startswith("https://"):
        return homepage
    return f"https://pypi.org/project/{name}/{version}/"


def _validate_spdx(expression: str, *, package: str) -> str:
    if expression not in SUPPORTED_SPDX_EXPRESSIONS:
        raise RuntimeError(f"unknown or unsupported SPDX license for {package}: {expression!r}")
    return expression


def _license_record(
    package_metadata: Mapping[str, Any], name: str, version: str
) -> dict[str, Any]:
    override = LICENSE_OVERRIDES.get((name, version))
    if override is not None:
        return {
            **override,
            "expression": _validate_spdx(override["expression"], package=name),
        }
    metadata_url = _metadata_url(name, version)
    expression = package_metadata.get("License-Expression")
    if isinstance(expression, str) and expression.strip():
        return {
            "expression": _validate_spdx(expression.strip(), package=name),
            "evidence": "core-metadata:License-Expression",
            "url": metadata_url,
        }

    license_field = package_metadata.get("License")
    if isinstance(license_field, str) and license_field.strip() in SUPPORTED_SPDX_EXPRESSIONS:
        return {
            "expression": license_field.strip(),
            "evidence": "core-metadata:License",
            "url": metadata_url,
        }

    classifier_expressions = {
        CLASSIFIER_LICENSES[classifier]
        for classifier in _metadata_values(package_metadata, "Classifier")
        if classifier in CLASSIFIER_LICENSES
    }
    if len(classifier_expressions) == 1:
        return {
            "expression": classifier_expressions.pop(),
            "evidence": "core-metadata:Classifier",
            "url": metadata_url,
        }
    if len(classifier_expressions) > 1:
        raise RuntimeError(f"conflicting license classifiers for {name}=={version}")

    raise RuntimeError(
        f"unknown license for {name}=={version}; add verified SPDX evidence before release"
    )


def _distribution_license_payloads(
    distribution: importlib.metadata.Distribution,
) -> list[tuple[str, bytes]]:
    payloads: list[tuple[str, bytes]] = []
    seen: set[str] = set()
    for entry in distribution.files or ():
        rendered = str(entry).replace("\\", "/")
        basename = Path(rendered).name
        lower = rendered.lower()
        if ".dist-info/licenses/" not in lower and not re.match(
            r"(?i)^(?:licen[cs]e|copying|notice|copyright)(?:[._-].*)?$", basename
        ):
            continue
        source = distribution.locate_file(entry)
        if not source.is_file():
            continue
        content = source.read_bytes()
        content_digest = digest_bytes(content)
        if content_digest in seen:
            continue
        seen.add(content_digest)
        payloads.append((basename, content))
    return sorted(payloads, key=lambda item: (item[0].casefold(), digest_bytes(item[1])))


def _notice_records(
    distribution: importlib.metadata.Distribution, name: str, version: str
) -> list[dict[str, str]]:
    payloads = _distribution_license_payloads(distribution)
    if not payloads:
        raise RuntimeError(f"installed distribution has no license notice file: {name}=={version}")
    records: list[dict[str, str]] = []
    for index, (basename, content) in enumerate(payloads, start=1):
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", basename).strip(".-") or "LICENSE.txt"
        records.append({
            "path": f"{LICENSE_ROOT}/python/{name}-{version}-{index}-{safe_name}",
            "sha256": digest_bytes(content),
        })
    return records


def build_runtime_manifest(lock_path: Path, project_version: str = VERSION) -> dict[str, Any]:
    dependencies: list[dict[str, Any]] = []
    locked = locked_dependencies(lock_path)
    _validate_reviewed_lock(locked)
    for name, version in locked:
        try:
            distribution = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise RuntimeError(f"locked dependency is not installed: {name}=={version}") from exc
        installed_version = distribution.version
        if installed_version != version:
            raise RuntimeError(
                f"installed dependency does not match lock: {name} locked={version} "
                f"installed={installed_version}"
            )
        metadata_name = distribution.metadata.get("Name") or name
        if canonical_name(str(metadata_name)) != name:
            raise RuntimeError(
                f"installed distribution identity mismatch: locked={name} metadata={metadata_name}"
            )
        license_record = _license_record(distribution.metadata, name, version)
        license_record["notices"] = _notice_records(distribution, name, version)
        expected_license = APPROVED_RUNTIME_LICENSES[(name, version)]
        if license_record["expression"] != expected_license:
            raise RuntimeError(
                f"reviewed license mismatch for {name}=={version}: "
                f"expected={expected_license} metadata={license_record['expression']}"
            )
        dependencies.append(
            {
                "name": name,
                "version": version,
                "purl": f"pkg:pypi/{name}@{version}",
                "source_url": _source_url(distribution.metadata, name, version),
                "metadata_url": _metadata_url(name, version),
                "license": license_record,
            }
        )
    return {
        "schema_version": 1,
        "component": {"name": "layman-codex", "version": project_version},
        "lock": {
            "path": "services/layman-router/requirements.lock",
            "sha256": digest(lock_path),
        },
        "dependencies": dependencies,
    }


def _validate_reviewed_lock(locked: Iterable[tuple[str, str]]) -> None:
    locked_set = set(locked)
    approved_set = set(APPROVED_RUNTIME_LICENSES)
    if locked_set != approved_set:
        raise RuntimeError(
            "runtime lock differs from the reviewed license policy: "
            f"unreviewed={sorted(locked_set - approved_set)}, "
            f"removed={sorted(approved_set - locked_set)}"
        )


def build_sbom(manifest: Mapping[str, Any]) -> dict[str, Any]:
    project = manifest["component"]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": project["name"],
                "version": project["version"],
                "purl": f"pkg:pypi/{project['name']}@{project['version']}",
                "licenses": [{"license": {"id": "MIT"}}],
            }
        },
        "components": [
            {
                "type": "library",
                "name": dependency["name"],
                "version": dependency["version"],
                "purl": dependency["purl"],
                "licenses": [
                    {"license": {"id": dependency["license"]["expression"]}}
                ],
                "properties": [
                    {
                        "name": "layman:source-url",
                        "value": dependency["source_url"],
                    },
                    {
                        "name": "layman:license-evidence",
                        "value": dependency["license"]["evidence"],
                    },
                    {
                        "name": "layman:license-url",
                        "value": dependency["license"]["url"],
                    },
                ],
            }
            for dependency in manifest["dependencies"]
        ],
    }


def write_json(path: Path, content: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(content, indent=2) + "\n").encode("utf-8"))


def write_runtime_license_bundle(manifest: Mapping[str, Any], target: Path) -> None:
    for dependency in manifest["dependencies"]:
        name, version = dependency["name"], dependency["version"]
        distribution = importlib.metadata.distribution(name)
        if distribution.version != version:
            raise RuntimeError(f"installed dependency changed while writing licenses: {name}")
        payloads = {digest_bytes(content): content for _, content in _distribution_license_payloads(distribution)}
        for notice in dependency["license"]["notices"]:
            content = payloads.get(notice["sha256"])
            if content is None:
                raise RuntimeError(f"license notice changed while writing bundle: {name}")
            destination = target / notice["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)


def _python_license_path() -> Path:
    bundled = ROOT / "third_party" / "cpython" / "LICENSE"
    if bundled.is_file():
        return bundled
    raise RuntimeError("reviewed CPython license file was not found in the repository")


def write_standalone_component_bundle(target: Path) -> dict[str, Any]:
    if platform.python_version() != CPYTHON_VERSION:
        raise RuntimeError(
            f"standalone CPython version is not release-pinned: expected={CPYTHON_VERSION} "
            f"running={platform.python_version()}"
        )
    python_license = _python_license_path().read_bytes()
    validate_cpython_license(python_license)
    pyinstaller = importlib.metadata.distribution("pyinstaller")
    if pyinstaller.version != PYINSTALLER_VERSION:
        raise RuntimeError(
            f"PyInstaller version is not release-pinned: expected={PYINSTALLER_VERSION} "
            f"installed={pyinstaller.version}"
        )
    pyinstaller_payloads = _distribution_license_payloads(pyinstaller)
    copying = next((content for name, content in pyinstaller_payloads if name.casefold() == "copying.txt"), None)
    if copying is None:
        raise RuntimeError("PyInstaller COPYING.txt was not found")

    licenses = {
        f"{LICENSE_ROOT}/CPython-LICENSE.txt": python_license,
        f"{LICENSE_ROOT}/PyInstaller-COPYING.txt": copying,
    }
    for relative, content in licenses.items():
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    manifest = {
        "schema_version": 1,
        "components": [
            {
                "name": "CPython",
                "version": CPYTHON_VERSION,
                "role": "embedded-runtime-and-standard-library",
                "source_license_url": CPYTHON_SOURCE_LICENSE_URL_TEMPLATE.format(
                    version=CPYTHON_VERSION
                ),
                "licenses": [{
                    "expression": "PSF-2.0",
                    "includes_incorporated_software_notices": True,
                    "path": f"{LICENSE_ROOT}/CPython-LICENSE.txt",
                    "sha256": digest_bytes(python_license),
                }],
            },
            {
                "name": "PyInstaller",
                "version": pyinstaller.version,
                "role": "embedded-bootloader-loader-and-runtime-hooks",
                "licenses": [
                    {
                        "expression": "GPL-2.0-or-later WITH Bootloader-exception",
                        "scope": "bootloader-and-loader",
                        "path": f"{LICENSE_ROOT}/PyInstaller-COPYING.txt",
                        "sha256": digest_bytes(copying),
                    },
                    {
                        "expression": "Apache-2.0",
                        "scope": "runtime-hooks",
                        "path": f"{LICENSE_ROOT}/PyInstaller-COPYING.txt",
                        "sha256": digest_bytes(copying),
                    },
                ],
            },
        ],
    }
    write_json(target / STANDALONE_MANIFEST_NAME, manifest)
    return manifest


def validate_runtime_manifest(lock_path: Path, manifest: Mapping[str, Any]) -> None:
    locked_items = locked_dependencies(lock_path)
    _validate_reviewed_lock(locked_items)
    locked = dict(locked_items)
    if manifest.get("schema_version") != 1:
        raise RuntimeError("runtime dependency manifest schema_version must be 1")
    if manifest.get("component") != {"name": "layman-codex", "version": VERSION}:
        raise RuntimeError("runtime dependency manifest has an unexpected component identity")
    lock = manifest.get("lock")
    if not isinstance(lock, dict) or lock.get("sha256") != digest(lock_path):
        raise RuntimeError("runtime dependency manifest lock digest does not match requirements.lock")
    if lock.get("path") != "services/layman-router/requirements.lock":
        raise RuntimeError("runtime dependency manifest lock path is unexpected")
    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, list):
        raise RuntimeError("runtime dependency manifest dependencies must be a list")
    manifest_map: dict[str, Mapping[str, Any]] = {}
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise RuntimeError("runtime dependency manifest contains a non-object dependency")
        name = canonical_name(str(dependency.get("name", "")))
        if not name or name in manifest_map:
            raise RuntimeError(f"invalid or duplicate runtime dependency: {name!r}")
        manifest_map[name] = dependency
    if set(manifest_map) != set(locked):
        raise RuntimeError(
            "runtime dependency manifest does not match lock: "
            f"missing={sorted(set(locked) - set(manifest_map))}, "
            f"unexpected={sorted(set(manifest_map) - set(locked))}"
        )
    for name, version in locked.items():
        dependency = manifest_map[name]
        if dependency.get("version") != version:
            raise RuntimeError(f"runtime dependency version mismatch for {name}")
        if dependency.get("purl") != f"pkg:pypi/{name}@{version}":
            raise RuntimeError(f"runtime dependency purl mismatch for {name}")
        for url_field in ("source_url", "metadata_url"):
            if not str(dependency.get(url_field, "")).startswith("https://"):
                raise RuntimeError(f"runtime dependency {url_field} is not traceable for {name}")
        license_record = dependency.get("license")
        if not isinstance(license_record, dict):
            raise RuntimeError(f"runtime dependency license is missing for {name}")
        expression = _validate_spdx(str(license_record.get("expression", "")), package=name)
        if expression != APPROVED_RUNTIME_LICENSES[(name, version)]:
            raise RuntimeError(f"runtime dependency license differs from reviewed policy for {name}")
        if not str(license_record.get("evidence", "")):
            raise RuntimeError(f"runtime dependency license evidence is missing for {name}")
        if not str(license_record.get("url", "")).startswith("https://"):
            raise RuntimeError(f"runtime dependency license URL is missing for {name}")
        notices = license_record.get("notices")
        if not isinstance(notices, list) or not notices:
            raise RuntimeError(f"runtime dependency license notice files are missing for {name}")
        for notice in notices:
            if not isinstance(notice, dict):
                raise RuntimeError(f"invalid runtime dependency notice for {name}")
            path = str(notice.get("path", ""))
            if not path.startswith(f"{LICENSE_ROOT}/python/") or Path(path).is_absolute() or ".." in Path(path).parts:
                raise RuntimeError(f"unsafe runtime dependency notice path for {name}")
            if not re.fullmatch(r"[0-9a-f]{64}", str(notice.get("sha256", ""))):
                raise RuntimeError(f"invalid runtime dependency notice digest for {name}")


def validate_standalone_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != 1:
        raise RuntimeError("standalone component manifest schema_version must be 1")
    components = manifest.get("components")
    if not isinstance(components, list):
        raise RuntimeError("standalone component manifest components must be a list")
    component_names = [
        str(component.get("name"))
        for component in components
        if isinstance(component, dict)
    ]
    if len(components) != 2 or len(component_names) != 2 or len(set(component_names)) != 2:
        raise RuntimeError("standalone component manifest must contain two unique components")
    by_name = {
        str(component.get("name")): component
        for component in components
        if isinstance(component, dict)
    }
    if set(by_name) != {"CPython", "PyInstaller"}:
        raise RuntimeError("standalone component manifest must identify CPython and PyInstaller")
    cpython = by_name["CPython"]
    if cpython.get("version") != CPYTHON_VERSION:
        raise RuntimeError("standalone component manifest has an unexpected CPython version")
    if cpython.get("role") != "embedded-runtime-and-standard-library":
        raise RuntimeError("standalone component manifest has an unexpected CPython role")
    if cpython.get("source_license_url") != CPYTHON_SOURCE_LICENSE_URL_TEMPLATE.format(
        version=CPYTHON_VERSION
    ):
        raise RuntimeError("standalone component manifest has an unexpected CPython license source")
    if by_name["PyInstaller"].get("version") != PYINSTALLER_VERSION:
        raise RuntimeError("standalone component manifest has an unexpected PyInstaller version")
    pyinstaller = by_name["PyInstaller"]
    if pyinstaller.get("role") != "embedded-bootloader-loader-and-runtime-hooks":
        raise RuntimeError("standalone component manifest has an unexpected PyInstaller role")
    expected_expressions = {
        "CPython": {"PSF-2.0"},
        "PyInstaller": {"GPL-2.0-or-later WITH Bootloader-exception", "Apache-2.0"},
    }
    for name, component in by_name.items():
        licenses = component.get("licenses")
        if not isinstance(licenses, list) or not licenses:
            raise RuntimeError(f"standalone component licenses are missing for {name}")
        expressions = {str(license_record.get("expression")) for license_record in licenses}
        if expressions != expected_expressions[name]:
            raise RuntimeError(f"standalone component license expressions are invalid for {name}")
        if name == "CPython":
            if len(licenses) != 1:
                raise RuntimeError("standalone CPython component must have exactly one license record")
            license_record = licenses[0]
            if license_record.get("includes_incorporated_software_notices") is not True:
                raise RuntimeError("standalone CPython license must include incorporated notices")
            if license_record.get("path") != f"{LICENSE_ROOT}/CPython-LICENSE.txt":
                raise RuntimeError("standalone CPython license path is unexpected")
            if license_record.get("sha256") != CPYTHON_LICENSE_SHA256:
                raise RuntimeError("standalone CPython license digest is unexpected")
        if name == "PyInstaller":
            expected_records = {
                (
                    "GPL-2.0-or-later WITH Bootloader-exception",
                    "bootloader-and-loader",
                    f"{LICENSE_ROOT}/PyInstaller-COPYING.txt",
                ),
                (
                    "Apache-2.0",
                    "runtime-hooks",
                    f"{LICENSE_ROOT}/PyInstaller-COPYING.txt",
                ),
            }
            actual_records = {
                (
                    str(record.get("expression")),
                    str(record.get("scope")),
                    str(record.get("path")),
                )
                for record in licenses
            }
            if len(licenses) != 2 or actual_records != expected_records:
                raise RuntimeError("standalone PyInstaller license records are invalid")
        for license_record in licenses:
            path = str(license_record.get("path", ""))
            if not path.startswith(f"{LICENSE_ROOT}/") or Path(path).is_absolute() or ".." in Path(path).parts:
                raise RuntimeError(f"unsafe standalone license path for {name}")
            if not re.fullmatch(r"[0-9a-f]{64}", str(license_record.get("sha256", ""))):
                raise RuntimeError(f"invalid standalone license digest for {name}")


def validate_bundle_audit(
    manifest: Mapping[str, Any],
    audit: Mapping[str, Any],
    *,
    executable_sha256: str,
) -> None:
    if audit.get("schema_version") != 1:
        raise RuntimeError("standalone bundle audit schema_version must be 1")
    for field in ("analysis_sha256", "executable_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(audit.get(field, ""))):
            raise RuntimeError(f"standalone bundle audit has an invalid {field}")
    if audit["executable_sha256"] != executable_sha256:
        raise RuntimeError("standalone executable differs from its bundle audit")
    if audit.get("unexpected") != [] or audit.get("unowned") != []:
        raise RuntimeError("standalone bundle audit contains unresolved files")

    expected = {
        canonical_name(dependency["name"]): str(dependency["version"])
        for dependency in manifest["dependencies"]
    }
    expected.update({"layman-codex": VERSION, "pyinstaller": PYINSTALLER_VERSION})
    distributions = audit.get("distributions")
    if not isinstance(distributions, list):
        raise RuntimeError("standalone bundle audit distributions must be a list")
    audited: dict[str, str] = {}
    for distribution in distributions:
        if not isinstance(distribution, dict):
            raise RuntimeError("standalone bundle audit contains an invalid distribution")
        name = canonical_name(str(distribution.get("name", "")))
        version = str(distribution.get("version", ""))
        file_count = distribution.get("file_count")
        if not name or name in audited or not isinstance(file_count, int) or file_count <= 0:
            raise RuntimeError(f"standalone bundle audit distribution is invalid: {name!r}")
        audited[name] = version
    if audited != expected:
        raise RuntimeError(
            "standalone bundle audit distributions differ from reviewed components: "
            f"expected={expected}, audited={audited}"
        )

    archive = audit.get("archive")
    if not isinstance(archive, dict):
        raise RuntimeError("standalone executable archive audit is missing")
    for field in ("carchive_entries", "pyz_entries", "python_roots"):
        if not isinstance(archive.get(field), int) or archive[field] <= 0:
            raise RuntimeError(f"standalone executable archive has an invalid {field}")
    for field in (
        "carchive_names_sha256",
        "pyz_names_sha256",
        "python_roots_sha256",
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", str(archive.get(field, ""))):
            raise RuntimeError(f"standalone executable archive has an invalid {field}")
    archive_distributions = archive.get("distributions")
    if archive_distributions != sorted(expected):
        raise RuntimeError(
            "standalone executable archive distributions differ from reviewed components"
        )

    build_tools = audit.get("build_tools")
    if not isinstance(build_tools, list):
        raise RuntimeError("standalone bundle audit build tools are missing")
    tool_names = [
        str(tool.get("name"))
        for tool in build_tools
        if isinstance(tool, dict)
    ]
    if len(build_tools) != 3 or len(tool_names) != 3 or len(set(tool_names)) != 3:
        raise RuntimeError("standalone bundle audit must contain three unique build tools")
    tools = {
        str(tool.get("name")): str(tool.get("version"))
        for tool in build_tools
        if isinstance(tool, dict)
    }
    if set(tools) != {"CPython", "PyInstaller", "pyinstaller-hooks-contrib"}:
        raise RuntimeError("standalone bundle audit build tools are incomplete")
    if tools["CPython"] != CPYTHON_VERSION:
        raise RuntimeError("standalone bundle audit CPython version is unexpected")
    if tools["PyInstaller"] != PYINSTALLER_VERSION:
        raise RuntimeError("standalone bundle audit PyInstaller version is unexpected")
    if tools["pyinstaller-hooks-contrib"] != PYINSTALLER_HOOKS_CONTRIB_VERSION:
        raise RuntimeError("standalone bundle audit hooks version is unexpected")


def validate_sbom(manifest: Mapping[str, Any], sbom: Mapping[str, Any]) -> None:
    if sbom.get("bomFormat") != "CycloneDX" or sbom.get("specVersion") != "1.5":
        raise RuntimeError("SBOM must use CycloneDX 1.5")
    expected_project = manifest["component"]
    expected_metadata_component = {
        "type": "application",
        "name": expected_project["name"],
        "version": expected_project["version"],
        "purl": f"pkg:pypi/{expected_project['name']}@{expected_project['version']}",
        "licenses": [{"license": {"id": "MIT"}}],
    }
    metadata = sbom.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("component") != expected_metadata_component:
        raise RuntimeError("SBOM has an unexpected application component identity")
    manifest_map = {dependency["name"]: dependency for dependency in manifest["dependencies"]}
    components = sbom.get("components")
    if not isinstance(components, list):
        raise RuntimeError("SBOM components must be a list")
    sbom_map: dict[str, Mapping[str, Any]] = {}
    for component in components:
        if not isinstance(component, dict):
            raise RuntimeError("SBOM contains a non-object component")
        name = canonical_name(str(component.get("name", "")))
        if not name or name in sbom_map:
            raise RuntimeError(f"invalid or duplicate SBOM component: {name!r}")
        sbom_map[name] = component
    if set(sbom_map) != set(manifest_map):
        raise RuntimeError("SBOM components do not match the runtime dependency manifest")
    for name, dependency in manifest_map.items():
        component = sbom_map[name]
        if component.get("version") != dependency["version"]:
            raise RuntimeError(f"SBOM version mismatch for {name}")
        if component.get("purl") != dependency["purl"]:
            raise RuntimeError(f"SBOM purl mismatch for {name}")
        licenses = component.get("licenses")
        expected = dependency["license"]["expression"]
        if licenses != [{"license": {"id": expected}}]:
            raise RuntimeError(f"SBOM license mismatch for {name}")


def validate_platform_archives(
    manifest: Mapping[str, Any], archives: Iterable[Path]
) -> None:
    expected_manifest = json.dumps(manifest, indent=2) + "\n"
    for archive_path in archives:
        archive_match = re.fullmatch(r"layman-(windows|macos|linux)-(.+)\.zip", archive_path.name)
        if archive_match is None:
            raise RuntimeError(f"platform archive filename is invalid: {archive_path.name}")
        expected_platform = f"{archive_match.group(1)}-{archive_match.group(2)}"
        expected_executable = "layman.exe" if archive_match.group(1) == "windows" else "layman"
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            required = {
                BUNDLE_AUDIT_NAME,
                MANIFEST_NAME,
                STANDALONE_MANIFEST_NAME,
                "THIRD_PARTY_NOTICES.md",
                "BUILD.json",
            }
            if not required <= names:
                raise RuntimeError(
                    f"platform archive is missing runtime compliance files: {archive_path.name}"
                )
            archived_manifest = archive.read(MANIFEST_NAME).decode("utf-8")
            if archived_manifest != expected_manifest:
                raise RuntimeError(
                    f"platform runtime manifest does not match release manifest: {archive_path.name}"
                )
            build = json.loads(archive.read("BUILD.json"))
            if (
                build.get("product") != "Layman"
                or build.get("version") != VERSION
                or build.get("platform") != expected_platform
                or build.get("executable") != expected_executable
            ):
                raise RuntimeError(f"platform BUILD.json identity is invalid: {archive_path.name}")
            inventory = build.get("runtime_dependencies")
            if not isinstance(inventory, dict):
                raise RuntimeError(f"platform BUILD.json lacks runtime dependency identity: {archive_path.name}")
            if inventory.get("path") != MANIFEST_NAME:
                raise RuntimeError(f"platform runtime manifest path mismatch: {archive_path.name}")
            if inventory.get("sha256") != digest_bytes(archived_manifest.encode("utf-8")):
                raise RuntimeError(f"platform runtime manifest digest mismatch: {archive_path.name}")
            if inventory.get("requirements_lock_sha256") != manifest["lock"]["sha256"]:
                raise RuntimeError(f"platform requirements lock digest mismatch: {archive_path.name}")
            for dependency in manifest["dependencies"]:
                for notice in dependency["license"]["notices"]:
                    if notice["path"] not in names:
                        raise RuntimeError(
                            f"platform runtime license notice is missing: {archive_path.name}:{notice['path']}"
                        )
                    if digest_bytes(archive.read(notice["path"])) != notice["sha256"]:
                        raise RuntimeError(
                            f"platform runtime license notice digest mismatch: {archive_path.name}:{notice['path']}"
                        )
            standalone_content = archive.read(STANDALONE_MANIFEST_NAME)
            standalone_manifest = json.loads(standalone_content)
            validate_standalone_manifest(standalone_manifest)
            standalone_identity = build.get("standalone_components")
            if not isinstance(standalone_identity, dict):
                raise RuntimeError(f"platform BUILD.json lacks standalone component identity: {archive_path.name}")
            if standalone_identity.get("path") != STANDALONE_MANIFEST_NAME:
                raise RuntimeError(f"platform standalone manifest path mismatch: {archive_path.name}")
            if standalone_identity.get("sha256") != digest_bytes(standalone_content):
                raise RuntimeError(f"platform standalone manifest digest mismatch: {archive_path.name}")
            if standalone_identity.get("components") != ["CPython", "PyInstaller"]:
                raise RuntimeError(f"platform standalone component identity mismatch: {archive_path.name}")
            embedded = standalone_identity.get("embedded_python_distributions")
            if (
                not isinstance(embedded, list)
                or not embedded
                or any(not isinstance(name, str) for name in embedded)
            ):
                raise RuntimeError(
                    f"platform embedded distribution audit is missing: {archive_path.name}"
                )
            normalized_embedded = [canonical_name(name) for name in embedded]
            if embedded != sorted(set(normalized_embedded)):
                raise RuntimeError(
                    f"platform embedded distribution audit is not canonical: {archive_path.name}"
                )
            allowed_embedded = {
                *(dependency["name"] for dependency in manifest["dependencies"]),
                "layman-codex",
                "pyinstaller",
            }
            unexpected_embedded = set(embedded) - allowed_embedded
            missing_embedded = allowed_embedded - set(embedded)
            if unexpected_embedded or missing_embedded:
                raise RuntimeError(
                    f"platform embedded distributions are not fully reviewed: {archive_path.name}: "
                    f"unexpected={sorted(unexpected_embedded)}, "
                    f"missing={sorted(missing_embedded)}"
                )
            audit_content = archive.read(BUNDLE_AUDIT_NAME)
            audit = json.loads(audit_content)
            executable_name = str(build.get("executable", ""))
            if executable_name not in names:
                raise RuntimeError(
                    f"platform executable is missing from archive: {archive_path.name}"
                )
            executable_sha256 = digest_bytes(archive.read(executable_name))
            validate_bundle_audit(
                manifest,
                audit,
                executable_sha256=executable_sha256,
            )
            audit_identity = build.get("bundle_audit")
            if not isinstance(audit_identity, dict):
                raise RuntimeError(
                    f"platform BUILD.json lacks bundle audit identity: {archive_path.name}"
                )
            if audit_identity.get("path") != BUNDLE_AUDIT_NAME:
                raise RuntimeError(
                    f"platform bundle audit path mismatch: {archive_path.name}"
                )
            if audit_identity.get("sha256") != digest_bytes(audit_content):
                raise RuntimeError(
                    f"platform bundle audit digest mismatch: {archive_path.name}"
                )
            if audit_identity.get("executable_sha256") != executable_sha256:
                raise RuntimeError(
                    f"platform executable digest identity mismatch: {archive_path.name}"
                )
            checked: set[str] = set()
            for component in standalone_manifest["components"]:
                for license_record in component["licenses"]:
                    path = license_record["path"]
                    if path in checked:
                        continue
                    checked.add(path)
                    if path not in names or digest_bytes(archive.read(path)) != license_record["sha256"]:
                        raise RuntimeError(
                            f"platform standalone license is missing or changed: {archive_path.name}:{path}"
                        )


def validate_release_runtime(
    lock_path: Path,
    manifest_path: Path,
    sbom_path: Path,
    platform_archives: Iterable[Path] = (),
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    validate_runtime_manifest(lock_path, manifest)
    validate_sbom(manifest, sbom)
    validate_platform_archives(manifest, platform_archives)


def _platform_archives(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.glob("*.zip")
        if PLATFORM_ARCHIVE_PATTERN.fullmatch(path.name)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument(
        "--lock",
        type=Path,
        default=ROOT / "services" / "layman-router" / "requirements.lock",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "release" / f"layman-v{VERSION}" / MANIFEST_NAME,
    )
    parser.add_argument(
        "--sbom",
        type=Path,
        default=ROOT / "release" / f"layman-v{VERSION}" / "sbom.cdx.json",
    )
    parser.add_argument("--platform-archives", type=Path)
    parser.add_argument("--project-version", default=VERSION)
    args = parser.parse_args()
    lock_path = args.lock.resolve()
    manifest_path = args.manifest.resolve()
    sbom_path = args.sbom.resolve()
    if args.command == "generate":
        manifest = build_runtime_manifest(lock_path, args.project_version)
        sbom = build_sbom(manifest)
        write_json(manifest_path, manifest)
        write_json(sbom_path, sbom)
    archives = _platform_archives(args.platform_archives.resolve()) if args.platform_archives else []
    validate_release_runtime(lock_path, manifest_path, sbom_path, archives)
    print(
        json.dumps(
            {
                "dependencies": len(json.loads(manifest_path.read_text(encoding="utf-8"))["dependencies"]),
                "manifest": str(manifest_path),
                "sbom": str(sbom_path),
                "platform_archives": [str(path) for path in archives],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
