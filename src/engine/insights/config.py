"""Configuration and project-local Skill loading."""

from hashlib import sha256
from typing import Any

import yaml

from src.core.config import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "egs" / "config" / "platform" / "insight_reports.yaml"
SKILL_ROOT = PROJECT_ROOT / "src" / "skills"


def insight_config() -> dict[str, Any]:
    return dict(yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")))


def load_skill(kind: str, config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    task = config["tasks"][kind]
    root = (SKILL_ROOT / task["skill_dir"]).resolve()
    if not root.is_relative_to(SKILL_ROOT.resolve()):
        raise ValueError(config["messages"]["bad_resource"])
    resources = {}
    content = []
    for name in task["resources"]:
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(config["messages"]["bad_resource"])
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        resources[name] = {"sha256": sha256(raw).hexdigest(), "text": text}
        content.append(f"--- {name} ---\n{text}")
    return "\n\n".join(content)[: config["defaults"]["max_skill_chars"]], resources
