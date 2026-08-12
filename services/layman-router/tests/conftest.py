from __future__ import annotations

from pathlib import Path

import pytest

from layman_router.config import load_config


@pytest.fixture
def router_config(tmp_path: Path):
    config = load_config()
    config.database_path = str(tmp_path / "usage.sqlite3")
    config.upstream_base_url = "https://upstream.test/v1"
    return config
