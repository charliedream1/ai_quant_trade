"""YAML owns workflow defaults and names; preview never generates model output."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import yaml

from src.agent.providers.config import backend_names
from src.agent.providers.contracts import ModelSelection
from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def settings() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/skill_workflows.yaml").read_text(encoding="utf-8"))


def local_file(value: str | Path) -> Path:
    path = Path(value).resolve()
    if not path.is_relative_to(PROJECT_ROOT.resolve()) or not path.is_file():
        raise ValueError("文件必须存在且位于本项目内")
    return path


def read_request(filename: str) -> dict:
    path = local_file(filename)
    if path.stat().st_size > settings()["limits"]["max_config_bytes"]:
        raise ValueError("Skill配置超过大小限制")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Skill配置必须为YAML对象")
    return value


def preview(payload: dict) -> dict:
    cfg = settings()
    if set(payload) - {"skill", "request", "provider", "imports"}:
        raise ValueError("Skill配置存在未知字段")
    skill = str(payload.get("skill") or "")
    if skill not in cfg["workflows"]:
        raise ValueError(cfg["messages"]["unknown"] + ": " + skill)
    workflow = cfg["workflows"][skill]
    if not isinstance(payload.get("request", {}), dict) or not isinstance(payload.get("provider", {}), dict):
        raise ValueError("request和provider必须为对象")
    request = {**workflow["defaults"], **payload.get("request", {})}
    if any(
        request.get(key) != value
        for key, value in workflow["defaults"].items()
        if key in {"kind", "workflow"} or key == "mode" and workflow["family"] == "alpha"
    ):
        raise ValueError("Skill家族与研究模式不一致")
    selection = ModelSelection.model_validate(payload.get("provider") or {"backend": "api"}).model_dump(
        exclude_none=True
    )
    if selection.get("backend", "api") not in backend_names():
        raise ValueError("未知生成后端")
    imports = payload.get("imports") or []
    if not isinstance(imports, list):
        raise ValueError("imports必须为列表")
    targets = set()
    for item in imports:
        if not isinstance(item, dict) or set(item) - {"target", "file", "kind", "name"}:
            raise ValueError("数据导入配置不合法")
        target = item.get("target")
        if (
            target not in {"dataset_id", "market_dataset_id", "documents_dataset_id", "memory_dataset_id"}
            or target in targets
        ):
            raise ValueError("导入目标不支持或重复")
        local_file(item["file"])
        targets.add(target)
    missing = [
        key
        for key in workflow["required"]
        if not request.get(key)
        and key not in targets
        and not (
            workflow["family"] == "alpha"
            and request.get("study_id")
            and key in {"name", "dataset_id", "cutoff", "configurations", "asset_mapping"}
        )
    ]
    if missing:
        raise ValueError(cfg["messages"]["missing"] + ": " + ", ".join(missing))
    resolved = {
        "skill": skill,
        "family": workflow["family"],
        "request": request,
        "provider": selection,
        "imports": imports,
    }
    return {
        **resolved,
        "digest": hashlib.sha256(json.dumps(resolved, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        "model_called": False,
        "web_required": False,
        "outer_cli_usage": None,
    }
