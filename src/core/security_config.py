"""Nonsecret project security policy. Credentials remain in environment files."""

from functools import lru_cache

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def security_config() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/security/security.yaml").read_text(encoding="utf-8"))
