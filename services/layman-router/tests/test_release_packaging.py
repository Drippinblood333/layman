from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import subprocess
import sys
import types
import zipfile
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[3]
PLATFORMS = {
    "layman-windows-x64": ("windows-x64", "layman.exe"),
    "layman-macos-x64": ("macos-x64", "layman"),
    "layman-macos-arm64": ("macos-arm64", "layman"),
    "layman-linux-x64": ("linux-x64", "layman"),
    "layman-linux-arm64": ("linux-arm64", "layman"),
}
FAKE_NOTICE_CONTENT = b"test license notice\n"


def runtime_inventory_module():
    spec = importlib.util.spec_from_file_location(
        "layman_test_runtime_inventory", ROOT / "scripts" / "runtime_inventory.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_runtime_compliance(lock_content: bytes | None = None) -> tuple[bytes, bytes]:
    inventory = runtime_inventory_module()
    if lock_content is None:
        lock_content = (
            ROOT / "services" / "layman-router" / "requirements.lock"
        ).read_bytes()
    lock_digest = hashlib.sha256(lock_content).hexdigest()
    manifest = {
        "schema_version": 1,
        "component": {"name": "layman-codex", "version": "1.0.0"},
        "lock": {
            "path": "services/layman-router/requirements.lock",
            "sha256": lock_digest,
        },
        "dependencies": [
            {
                "name": name,
                "version": version,
                "purl": f"pkg:pypi/{name}@{version}",
                "source_url": f"https://example.test/{name}",
                "metadata_url": f"https://pypi.org/pypi/{name}/{version}/json",
                "license": {
                    "expression": expression,
                    "evidence": "reviewed-test-fixture",
                    "url": f"https://pypi.org/pypi/{name}/{version}/json",
                    "notices": [{
                        "path": f"THIRD_PARTY_LICENSES/python/{name}-{version}-1-LICENSE.txt",
                        "sha256": hashlib.sha256(FAKE_NOTICE_CONTENT).hexdigest(),
                    }],
                },
            }
            for (name, version), expression in sorted(
                inventory.APPROVED_RUNTIME_LICENSES.items()
            )
        ],
    }
    sbom = inventory.build_sbom(manifest)
    return (
        (json.dumps(manifest, indent=2) + "\n").encode(),
        (json.dumps(sbom, indent=2) + "\n").encode(),
    )


def fake_standalone_compliance() -> tuple[bytes, dict[str, bytes]]:
    inventory = runtime_inventory_module()
    cpython_license = (ROOT / "third_party" / "cpython" / "LICENSE").read_bytes()
    licenses = {
        "THIRD_PARTY_LICENSES/CPython-LICENSE.txt": cpython_license,
        "THIRD_PARTY_LICENSES/PyInstaller-COPYING.txt": b"pyinstaller license\n",
    }
    manifest = {
        "schema_version": 1,
        "components": [
            {
                "name": "CPython",
                "version": inventory.CPYTHON_VERSION,
                "role": "embedded-runtime-and-standard-library",
                "source_license_url": inventory.CPYTHON_SOURCE_LICENSE_URL_TEMPLATE.format(
                    version=inventory.CPYTHON_VERSION
                ),
                "licenses": [{
                    "expression": "PSF-2.0",
                    "includes_incorporated_software_notices": True,
                    "path": "THIRD_PARTY_LICENSES/CPython-LICENSE.txt",
                    "sha256": hashlib.sha256(licenses["THIRD_PARTY_LICENSES/CPython-LICENSE.txt"]).hexdigest(),
                }],
            },
            {
                "name": "PyInstaller",
                "version": "6.22.0",
                "role": "embedded-bootloader-loader-and-runtime-hooks",
                "licenses": [
                    {
                        "expression": "GPL-2.0-or-later WITH Bootloader-exception",
                        "scope": "bootloader-and-loader",
                        "path": "THIRD_PARTY_LICENSES/PyInstaller-COPYING.txt",
                        "sha256": hashlib.sha256(licenses["THIRD_PARTY_LICENSES/PyInstaller-COPYING.txt"]).hexdigest(),
                    },
                    {
                        "expression": "Apache-2.0",
                        "scope": "runtime-hooks",
                        "path": "THIRD_PARTY_LICENSES/PyInstaller-COPYING.txt",
                        "sha256": hashlib.sha256(licenses["THIRD_PARTY_LICENSES/PyInstaller-COPYING.txt"]).hexdigest(),
                    },
                ],
            },
        ],
    }
    return (json.dumps(manifest, indent=2) + "\n").encode(), licenses


def fake_bundle_audit(
    runtime_manifest: dict[str, object], executable: bytes = b"binary"
) -> bytes:
    inventory = runtime_inventory_module()
    dependencies = runtime_manifest["dependencies"]
    assert isinstance(dependencies, list)
    versions = {
        str(dependency["name"]): str(dependency["version"])
        for dependency in dependencies
    }
    versions.update(
        {
            "layman-codex": "1.0.0",
            "pyinstaller": inventory.PYINSTALLER_VERSION,
        }
    )
    audit = {
        "schema_version": 1,
        "analysis_sha256": "0" * 64,
        "executable_sha256": hashlib.sha256(executable).hexdigest(),
        "distributions": [
            {"name": name, "version": versions[name], "file_count": 1}
            for name in sorted(versions)
        ],
        "archive": {
            "carchive_entries": 1,
            "carchive_names_sha256": "1" * 64,
            "pyz_entries": 1,
            "pyz_names_sha256": "2" * 64,
            "python_roots": 1,
            "python_roots_sha256": "3" * 64,
            "distributions": sorted(versions),
        },
        "build_tools": [
            {"name": "CPython", "version": inventory.CPYTHON_VERSION},
            {"name": "PyInstaller", "version": inventory.PYINSTALLER_VERSION},
            {
                "name": "pyinstaller-hooks-contrib",
                "version": inventory.PYINSTALLER_HOOKS_CONTRIB_VERSION,
            },
        ],
        "unexpected": [],
        "unowned": [],
    }
    return (json.dumps(audit, indent=2) + "\n").encode()


def run_script(name: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / name), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_platform_artifacts_are_packaged_as_root_level_release_zips(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    output = tmp_path / "release"
    lock_content = (ROOT / "services" / "layman-router" / "requirements.lock").read_bytes()
    manifest_content, _ = fake_runtime_compliance(lock_content)
    standalone_content, standalone_licenses = fake_standalone_compliance()
    runtime_manifest = json.loads(manifest_content)
    audit_content = fake_bundle_audit(runtime_manifest)
    embedded_names = json.loads(audit_content)["archive"]["distributions"]
    for artifact, (platform, executable) in PLATFORMS.items():
        directory = artifacts / artifact
        directory.mkdir(parents=True)
        (directory / executable).write_bytes(b"binary")
        (directory / "runtime-dependencies.json").write_bytes(manifest_content)
        (directory / "standalone-components.json").write_bytes(standalone_content)
        (directory / "bundle-audit.json").write_bytes(audit_content)
        (directory / "THIRD_PARTY_NOTICES.md").write_text("notices", encoding="utf-8")
        for dependency in runtime_manifest["dependencies"]:
            for notice in dependency["license"]["notices"]:
                notice_path = directory / notice["path"]
                notice_path.parent.mkdir(parents=True, exist_ok=True)
                notice_path.write_bytes(FAKE_NOTICE_CONTENT)
        for relative, content in standalone_licenses.items():
            license_path = directory / relative
            license_path.parent.mkdir(parents=True, exist_ok=True)
            license_path.write_bytes(content)
        (directory / "BUILD.json").write_text(
            json.dumps(
                {
                    "platform": platform,
                    "executable": executable,
                    "runtime_dependencies": {
                        "path": "runtime-dependencies.json",
                        "sha256": hashlib.sha256(manifest_content).hexdigest(),
                        "requirements_lock_sha256": hashlib.sha256(lock_content).hexdigest(),
                    },
                    "standalone_components": {
                        "path": "standalone-components.json",
                        "sha256": hashlib.sha256(standalone_content).hexdigest(),
                        "components": ["CPython", "PyInstaller"],
                        "embedded_python_distributions": embedded_names,
                    },
                    "bundle_audit": {
                        "path": "bundle-audit.json",
                        "sha256": hashlib.sha256(audit_content).hexdigest(),
                        "executable_sha256": hashlib.sha256(b"binary").hexdigest(),
                    },
                }
            ),
            encoding="utf-8",
        )

    result = run_script(
        "package-platform-artifacts.py", "--artifacts", str(artifacts), "--output", str(output)
    )
    assert result.returncode == 0, result.stderr
    for artifact, (_, executable) in PLATFORMS.items():
        archive = output / f"{artifact}.zip"
        assert archive.is_file()
        with zipfile.ZipFile(archive) as package:
            assert {
                executable,
                "BUILD.json",
                "runtime-dependencies.json",
                "standalone-components.json",
                "bundle-audit.json",
                "THIRD_PARTY_NOTICES.md",
            } <= set(package.namelist())
            assert any(name.startswith("THIRD_PARTY_LICENSES/python/") for name in package.namelist())
            assert "THIRD_PARTY_LICENSES/CPython-LICENSE.txt" in package.namelist()
            assert "THIRD_PARTY_LICENSES/PyInstaller-COPYING.txt" in package.namelist()
            executable_info = package.getinfo(executable)
            executable_mode = executable_info.external_attr >> 16
            assert executable_info.create_system == 3
            if artifact.startswith(("layman-linux-", "layman-macos-")):
                assert stat.S_ISREG(executable_mode)
                assert executable_mode & 0o777 == 0o755
            else:
                assert executable_mode & 0o777 == 0o644
            assert package.getinfo("BUILD.json").external_attr >> 16 & 0o777 == 0o644


def test_docker_build_uses_repository_context_and_includes_plugin_sources():
    compose_path = ROOT / "services" / "layman-router" / "docker-compose.yml"
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    build = compose["services"]["layman-router"]["build"]
    assert (compose_path.parent / build["context"]).resolve() == ROOT
    assert build["dockerfile"] == "services/layman-router/Dockerfile"

    dockerfile = (ROOT / build["dockerfile"]).read_text(encoding="utf-8")
    assert dockerfile.startswith(
        "FROM python:3.14.3-slim@sha256:"
        "5e59aae31ff0e87511226be8e2b94d78c58f05216efda3b07dbbed938ec8583b\n"
    )
    assert "services/layman-router/hatch_build.py" in dockerfile
    assert "services/layman-router/requirements.lock" in dockerfile
    assert "pip install --no-cache-dir --require-hashes -r requirements.lock" in dockerfile
    assert "pip install --no-cache-dir --no-deps ." in dockerfile
    assert "pip check" in dockerfile
    assert ".agents/plugins/marketplace.json" in dockerfile
    assert "plugins/layman" in dockerfile


def test_ci_quality_tools_are_version_pinned_in_the_dev_extra():
    pyproject = (ROOT / "services" / "layman-router" / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    for requirement in (
        "pytest==9.1.1",
        "pytest-asyncio==1.4.0",
        "Pillow==12.3.0",
        "ruff==0.15.21",
        "bandit==1.9.4",
        "pip-audit==2.10.1",
    ):
        assert f'"{requirement}"' in pyproject

    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    assert 'python -m pip install -e "./services/layman-router[dev]"' in workflow
    assert '"./services/layman-router[dev]" ruff bandit pip-audit' not in workflow


def test_hatch_build_finds_plugin_bundle_in_shallow_project_root(
    tmp_path: Path, monkeypatch
):
    interface = types.ModuleType("hatchling.builders.hooks.plugin.interface")

    class StubBuildHookInterface:
        pass

    interface.BuildHookInterface = StubBuildHookInterface
    module_names = [
        "hatchling",
        "hatchling.builders",
        "hatchling.builders.hooks",
        "hatchling.builders.hooks.plugin",
    ]
    modules = {name: types.ModuleType(name) for name in module_names}
    modules["hatchling.builders.hooks.plugin.interface"] = interface
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    spec = importlib.util.spec_from_file_location(
        "layman_test_hatch_build", ROOT / "services" / "layman-router" / "hatch_build.py"
    )
    assert spec is not None and spec.loader is not None
    hatch_build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hatch_build)

    project = tmp_path / "app"
    manifest = project / ".agents" / "plugins" / "marketplace.json"
    plugin = project / "plugins" / "layman"
    manifest.parent.mkdir(parents=True)
    plugin.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    (plugin / "README.md").write_text("plugin", encoding="utf-8")

    hook = hatch_build.CustomBuildHook()
    hook.root = str(project)
    hook.target_name = "wheel"
    build_data = {"force_include": {}}
    hook.initialize("1.0.0", build_data)

    assert build_data["force_include"] == {
        str(manifest): "layman_router/bundle/.agents/plugins/marketplace.json",
        str(plugin): "layman_router/bundle/plugins/layman",
    }


def test_runtime_inventory_matches_lock_and_emits_traceable_spdx_licenses(tmp_path: Path):
    inventory = runtime_inventory_module()
    lock_path = tmp_path / "requirements.lock"
    lock_content = (ROOT / "services" / "layman-router" / "requirements.lock").read_bytes()
    lock_path.write_bytes(lock_content)
    manifest_content, _ = fake_runtime_compliance(lock_content)
    manifest = json.loads(manifest_content)
    inventory.validate_runtime_manifest(lock_path, manifest)

    locked = dict(inventory.locked_dependencies(lock_path))
    dependencies = {item["name"]: item for item in manifest["dependencies"]}
    assert {name: item["version"] for name, item in dependencies.items()} == locked
    assert all(
        item["license"]["expression"] in inventory.SUPPORTED_SPDX_EXPRESSIONS
        and item["license"]["evidence"]
        and item["license"]["url"].startswith("https://")
        and item["source_url"].startswith("https://")
        and item["metadata_url"].startswith("https://")
        for item in dependencies.values()
    )
    assert all(item["license"]["notices"] for item in dependencies.values())
    assert inventory._license_record(
        {"License": "MPL-2.0"}, "certifi", "2026.7.22"
    )["expression"] == "MPL-2.0"
    assert inventory._license_record(
        {"Classifier": ["License :: OSI Approved :: BSD License"]},
        "colorama",
        "0.4.6",
    ) == {
        "expression": "BSD-3-Clause",
        "evidence": "curated-upstream-license",
        "url": "https://github.com/tartley/colorama/blob/3de9f013df4b470069d03d250224062e8cf15c49/LICENSE.txt",
    }
    real_lock = set(
        inventory.locked_dependencies(
            ROOT / "services" / "layman-router" / "requirements.lock"
        )
    )
    assert inventory.APPROVED_RUNTIME_LICENSES == {
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
    assert set(inventory.APPROVED_RUNTIME_LICENSES) == real_lock
    assert set(inventory.LICENSE_OVERRIDES) <= real_lock
    assert all(
        record["expression"] in inventory.SUPPORTED_SPDX_EXPRESSIONS
        and record["url"].startswith("https://github.com/")
        for record in inventory.LICENSE_OVERRIDES.values()
    )

    sbom = inventory.build_sbom(manifest)
    inventory.validate_sbom(manifest, sbom)
    standalone_content, _ = fake_standalone_compliance()
    inventory.validate_standalone_manifest(json.loads(standalone_content))
    first_name = manifest["dependencies"][0]["name"]
    sbom["components"][0]["licenses"] = [{"license": {"id": "MIT"}}]
    if dependencies[first_name]["license"]["expression"] == "MIT":
        sbom["components"][0]["licenses"] = [{"license": {"id": "BSD-3-Clause"}}]
    with pytest.raises(RuntimeError, match="SBOM license mismatch"):
        inventory.validate_sbom(manifest, sbom)


def test_runtime_inventory_rejects_unknown_license_metadata():
    inventory = runtime_inventory_module()
    with pytest.raises(RuntimeError, match="unknown license"):
        inventory._license_record(
            {
                "Name": "mystery-package",
                "Project-URL": "Source, https://example.test/source",
            },
            "mystery-package",
            "1.0",
        )


def test_runtime_manifest_and_sbom_reject_project_identity_tampering(tmp_path: Path):
    inventory = runtime_inventory_module()
    lock_path = tmp_path / "requirements.lock"
    lock_content = (ROOT / "services" / "layman-router" / "requirements.lock").read_bytes()
    lock_path.write_bytes(lock_content)
    manifest_content, _ = fake_runtime_compliance(lock_content)
    manifest = json.loads(manifest_content)
    manifest["component"]["version"] = "9.9.9"
    with pytest.raises(RuntimeError, match="component identity"):
        inventory.validate_runtime_manifest(lock_path, manifest)

    valid_manifest = json.loads(fake_runtime_compliance(lock_content)[0])
    sbom = inventory.build_sbom(valid_manifest)
    sbom["metadata"]["component"]["name"] = "other-project"
    with pytest.raises(RuntimeError, match="application component identity"):
        inventory.validate_sbom(valid_manifest, sbom)


def test_repository_cpython_license_is_complete_cross_platform():
    inventory = runtime_inventory_module()
    bundled = ROOT / "third_party" / "cpython" / "LICENSE"
    assert bundled.is_file()
    inventory.validate_cpython_license(bundled.read_bytes())
    assert inventory._python_license_path() == bundled
    with pytest.raises(RuntimeError, match="reviewed source digest"):
        inventory.validate_cpython_license(b"PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("version", "3.14.2", "unexpected CPython version"),
        ("role", "runtime", "unexpected CPython role"),
        ("source_license_url", "https://example.test/LICENSE", "unexpected CPython license source"),
    ],
)
def test_standalone_manifest_rejects_cpython_identity_tampering(
    field: str, value: str, message: str
):
    inventory = runtime_inventory_module()
    standalone_content, _ = fake_standalone_compliance()
    manifest = json.loads(standalone_content)
    manifest["components"][0][field] = value
    with pytest.raises(RuntimeError, match=message):
        inventory.validate_standalone_manifest(manifest)


def test_standalone_manifest_rejects_cpython_license_tampering():
    inventory = runtime_inventory_module()
    standalone_content, _ = fake_standalone_compliance()
    manifest = json.loads(standalone_content)
    manifest["components"][0]["licenses"][0]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="CPython license digest"):
        inventory.validate_standalone_manifest(manifest)


def test_standalone_manifest_rejects_duplicate_components():
    inventory = runtime_inventory_module()
    standalone_content, _ = fake_standalone_compliance()
    manifest = json.loads(standalone_content)
    manifest["components"].append(manifest["components"][0].copy())
    with pytest.raises(RuntimeError, match="two unique components"):
        inventory.validate_standalone_manifest(manifest)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("role", "bootloader", "unexpected PyInstaller role"),
        ("scope", "all-files", "PyInstaller license records"),
    ],
)
def test_standalone_manifest_rejects_pyinstaller_identity_tampering(
    field: str, value: str, message: str
):
    inventory = runtime_inventory_module()
    standalone_content, _ = fake_standalone_compliance()
    manifest = json.loads(standalone_content)
    pyinstaller = manifest["components"][1]
    if field == "role":
        pyinstaller[field] = value
    else:
        pyinstaller["licenses"][0][field] = value
    with pytest.raises(RuntimeError, match=message):
        inventory.validate_standalone_manifest(manifest)


def test_bundle_audit_rejects_unpinned_cpython_build():
    inventory = runtime_inventory_module()
    lock_content = (ROOT / "services" / "layman-router" / "requirements.lock").read_bytes()
    manifest_content, _ = fake_runtime_compliance(lock_content)
    runtime_manifest = json.loads(manifest_content)
    audit = json.loads(fake_bundle_audit(runtime_manifest))
    audit["build_tools"][0]["version"] = "3.14.2"
    with pytest.raises(RuntimeError, match="CPython version is unexpected"):
        inventory.validate_bundle_audit(
            runtime_manifest,
            audit,
            executable_sha256=hashlib.sha256(b"binary").hexdigest(),
        )


def test_bundle_audit_rejects_duplicate_build_tools():
    inventory = runtime_inventory_module()
    lock_content = (ROOT / "services" / "layman-router" / "requirements.lock").read_bytes()
    manifest_content, _ = fake_runtime_compliance(lock_content)
    runtime_manifest = json.loads(manifest_content)
    audit = json.loads(fake_bundle_audit(runtime_manifest))
    audit["build_tools"].append(audit["build_tools"][0].copy())
    with pytest.raises(RuntimeError, match="three unique build tools"):
        inventory.validate_bundle_audit(
            runtime_manifest,
            audit,
            executable_sha256=hashlib.sha256(b"binary").hexdigest(),
        )


def test_standalone_analysis_rejects_unreviewed_embedded_distributions(
    tmp_path: Path,
):
    inventory = runtime_inventory_module()
    site_packages = tmp_path / "Lib" / "site-packages"
    allowed_file = site_packages / "allowed_pkg" / "module.py"
    unexpected_file = site_packages / "build_tool" / "module.py"
    allowed_file.parent.mkdir(parents=True)
    unexpected_file.parent.mkdir(parents=True)
    allowed_file.write_text("", encoding="utf-8")
    unexpected_file.write_text("", encoding="utf-8")
    analysis = tmp_path / "Analysis-00.toc"

    class FakeDistribution:
        def __init__(self, name: str, relative: Path):
            self.metadata = {"Name": name}
            self.files = [relative]
            self.version = "1.0"

        def locate_file(self, entry: Path) -> Path:
            return site_packages / entry

    allowed = FakeDistribution("allowed-pkg", Path("allowed_pkg/module.py"))
    unexpected = FakeDistribution("build-tool", Path("build_tool/module.py"))
    analysis.write_text(
        repr(([('build_tool.module', str(unexpected_file), 'PYMODULE')],)),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="build-tool"):
        inventory.validate_embedded_distributions(
            analysis,
            tmp_path / "standalone.exe",
            {"allowed-pkg": "1.0"},
            distributions=[allowed, unexpected],
        )


def test_staged_release_assets_are_flat_and_match_checksums(tmp_path: Path):
    release = tmp_path / "release"
    output = tmp_path / "public-assets"
    lock_content = (ROOT / "services" / "layman-router" / "requirements.lock").read_bytes()
    manifest_content, sbom_content = fake_runtime_compliance(lock_content)
    standalone_content, standalone_licenses = fake_standalone_compliance()
    runtime_manifest = json.loads(manifest_content)
    audit_content = fake_bundle_audit(runtime_manifest)
    embedded_names = json.loads(audit_content)["archive"]["distributions"]
    (release / "python").mkdir(parents=True)
    (release / "legacy").mkdir()
    files = {
        release / "layman-codex-plugin-1.0.0.zip": b"plugin",
        release / "python" / "layman_codex-1.0.0-py3-none-any.whl": b"wheel",
        release / "python" / "layman_codex-1.0.0.tar.gz": b"sdist",
        release / "legacy" / "layman-skill-v1.zip": b"legacy",
        release / "legacy" / "layman-skill-v1.zip.sha256": b"legacy-checksum",
        release / "sbom.cdx.json": sbom_content,
        release / "runtime-dependencies.json": manifest_content,
        release / "requirements.lock": lock_content,
        release / "RELEASE_NOTES.md": b"notes",
        release / "README.md": b"readme",
        release / "README.zh-CN.md": b"readme-zh",
        release / "LICENSE": b"license",
        release / "THIRD_PARTY_NOTICES.md": b"notices",
        release / "SECURITY.md": b"security",
    }
    for path, content in files.items():
        path.write_bytes(content)
    with zipfile.ZipFile(release / "layman-windows-x64.zip", "w") as package:
        package.writestr("layman.exe", b"binary")
        package.writestr("runtime-dependencies.json", manifest_content)
        package.writestr("standalone-components.json", standalone_content)
        package.writestr("bundle-audit.json", audit_content)
        package.writestr("THIRD_PARTY_NOTICES.md", b"notices")
        for dependency in runtime_manifest["dependencies"]:
            for notice in dependency["license"]["notices"]:
                package.writestr(notice["path"], FAKE_NOTICE_CONTENT)
        for relative, content in standalone_licenses.items():
            package.writestr(relative, content)
        package.writestr(
            "BUILD.json",
            json.dumps(
                {
                    "product": "Layman",
                    "version": "1.0.0",
                    "platform": "windows-x64",
                    "executable": "layman.exe",
                    "runtime_dependencies": {
                        "path": "runtime-dependencies.json",
                        "sha256": hashlib.sha256(manifest_content).hexdigest(),
                        "requirements_lock_sha256": hashlib.sha256(lock_content).hexdigest(),
                    },
                    "standalone_components": {
                        "path": "standalone-components.json",
                        "sha256": hashlib.sha256(standalone_content).hexdigest(),
                        "components": ["CPython", "PyInstaller"],
                        "embedded_python_distributions": embedded_names,
                    },
                    "bundle_audit": {
                        "path": "bundle-audit.json",
                        "sha256": hashlib.sha256(audit_content).hexdigest(),
                        "executable_sha256": hashlib.sha256(b"binary").hexdigest(),
                    },
                }
            ).encode(),
        )

    result = run_script(
        "stage-release-assets.py", "--release", str(release), "--output", str(output)
    )
    assert result.returncode == 0, result.stderr
    checksums = json.loads((output / "SHA256SUMS.json").read_text(encoding="utf-8"))
    assert "layman-windows-x64.zip" in checksums
    assert "runtime-dependencies.json" in checksums
    assert all("/" not in name and "\\" not in name for name in checksums)
    for name, expected in checksums.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest().upper() == expected

    strict = run_script(
        "stage-release-assets.py",
        "--release",
        str(release),
        "--output",
        str(tmp_path / "strict-assets"),
        "--require-all-platforms",
    )
    assert strict.returncode != 0
    assert "required platform archive not found" in strict.stderr

    existing_external = tmp_path / "existing-output"
    existing_external.mkdir()
    marker = existing_external / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    unsafe = run_script(
        "stage-release-assets.py",
        "--release",
        str(release),
        "--output",
        str(existing_external),
    )
    assert unsafe.returncode != 0
    assert "refusing unsafe staging cleanup target" in unsafe.stderr
    assert marker.read_text(encoding="utf-8") == "keep"
