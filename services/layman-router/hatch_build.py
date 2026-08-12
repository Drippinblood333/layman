from __future__ import annotations

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Bundle the public Codex plugin into every Python distribution."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        project = Path(self.root).resolve()
        repository = project.parents[1]
        repository_manifest = repository / ".agents" / "plugins" / "marketplace.json"
        repository_plugin = repository / "plugins" / "layman"
        packaged = project / "src" / "layman_router" / "bundle"
        packaged_manifest = packaged / ".agents" / "plugins" / "marketplace.json"
        packaged_plugin = packaged / "plugins" / "layman"

        if self.target_name == "wheel":
            if packaged_manifest.is_file() and packaged_plugin.is_dir():
                # The normal wheel selector already includes the copy embedded in an sdist.
                return
            destination = "layman_router/bundle"
        elif self.target_name == "sdist":
            destination = "src/layman_router/bundle"
        else:
            return

        if repository_manifest.is_file() and repository_plugin.is_dir():
            manifest, plugin = repository_manifest, repository_plugin
        else:
            raise RuntimeError(
                "Layman plugin bundle is missing; expected the repository plugin "
                "or the copy embedded in the source distribution"
            )

        force_include = build_data["force_include"]
        force_include[str(manifest)] = f"{destination}/.agents/plugins/marketplace.json"
        force_include[str(plugin)] = f"{destination}/plugins/layman"
