from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .models import ProjectConfig, RouterConfig


REPO_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "projects.yaml"
BUNDLED_CONFIG_PATH = Path(__file__).with_name("default_config.yaml")


def load_config(path: str | Path | None = None) -> RouterConfig:
    configured = path or os.getenv("LAYMAN_ROUTER_CONFIG") or (REPO_CONFIG_PATH if REPO_CONFIG_PATH.exists() else BUNDLED_CONFIG_PATH)
    config_path = Path(configured).expanduser().resolve()
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Router config must be a YAML object: {config_path}")
    config = RouterConfig.model_validate(data)
    if os.getenv("LAYMAN_ROUTER_UPSTREAM_BASE_URL"):
        config.upstream_base_url = os.environ["LAYMAN_ROUTER_UPSTREAM_BASE_URL"]
    if os.getenv("LAYMAN_ROUTER_DATABASE_PATH"):
        config.database_path = os.environ["LAYMAN_ROUTER_DATABASE_PATH"]
    if os.getenv("LAYMAN_ROUTER_HOST"):
        config.listen_host = os.environ["LAYMAN_ROUTER_HOST"]
    if os.getenv("LAYMAN_ROUTER_PORT"):
        config.listen_port = int(os.environ["LAYMAN_ROUTER_PORT"])
    if os.getenv("LAYMAN_ROUTER_ADMIN_ALLOW_NON_LOOPBACK"):
        config.admin_allow_non_loopback = os.environ["LAYMAN_ROUTER_ADMIN_ALLOW_NON_LOOPBACK"].lower() in {"1", "true", "yes"}
    if os.getenv("LAYMAN_ROUTER_DEMO"):
        config.demo_mode = os.environ["LAYMAN_ROUTER_DEMO"].lower() in {"1", "true", "yes"}
    database_path = Path(config.database_path).expanduser()
    if not database_path.is_absolute():
        database_path = (config_path.parent / database_path).resolve()
    config.database_path = str(database_path)
    return config


def project_settings(config: RouterConfig, metadata: dict[str, Any]) -> tuple[str, ProjectConfig, str, str]:
    project_id = str(metadata.get("layman_project_id") or "default")
    project = config.projects.get(project_id) or config.projects.get("default") or ProjectConfig()
    quality = str(metadata.get("layman_quality") or project.default_quality)
    budget = str(metadata.get("layman_budget") or project.default_budget)
    if quality not in {"economy", "standard", "production"}:
        quality = project.default_quality
    if budget not in {"low", "medium", "high"}:
        budget = project.default_budget
    return project_id, project, quality, budget
