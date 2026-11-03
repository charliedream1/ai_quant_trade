"""Load nonsecret economic data contracts and presentation defaults."""

from functools import lru_cache

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def economics_config() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/economic_analysis.yaml").read_text(encoding="utf-8"))
