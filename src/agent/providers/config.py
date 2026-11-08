"""Project-owned provider settings; credentials stay in the environment."""

from functools import lru_cache

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def provider_config() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/agents/agent_providers.yaml").read_text(encoding="utf-8"))


def backend_names() -> set[str]:
    return set(provider_config()["providers"])


def backend_choices() -> list[tuple[str, str]]:
    return [(value["label"], key) for key, value in provider_config()["providers"].items()]
