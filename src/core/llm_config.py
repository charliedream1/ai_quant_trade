"""Ordinary generation defaults and connectivity prompts are project YAML."""

from functools import lru_cache

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def llm_config() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/models/llm_client.yaml").read_text(encoding="utf-8"))
