"""Versioned settings for concise diagnostics and bounded UI work."""

from functools import lru_cache

import yaml

from .config import PROJECT_ROOT


@lru_cache(maxsize=1)
def diagnostics_config():
    return yaml.safe_load((PROJECT_ROOT / "egs/config/ui/runtime_diagnostics.yaml").read_text(encoding="utf-8"))
