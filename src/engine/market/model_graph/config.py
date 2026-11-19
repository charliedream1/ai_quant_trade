"""Versioned graph policy and canonical Skill instructions."""

from functools import lru_cache
from hashlib import sha256

import yaml

from src.core.config import PROJECT_ROOT
from src.core.paths import SOURCE_ROOT


@lru_cache(maxsize=1)
def config():
    return yaml.safe_load((PROJECT_ROOT / "egs/config/data/model_relation_graph.yaml").read_text(encoding="utf-8"))


def skill():
    text = (SOURCE_ROOT / "src/skills/quant-stock-relations/SKILL.md").read_text(encoding="utf-8")
    return text, sha256(text.encode("utf-8")).hexdigest()
