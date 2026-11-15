"""Interaction settings shared by the browser and callback adapters."""

from functools import lru_cache

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def workspace_config() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/ui/research_workspace.yaml").read_text(encoding="utf-8"))
