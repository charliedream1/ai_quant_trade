"""Tracked project-only copies; unknown same-name files are never overwritten."""

import hashlib
import json
from pathlib import Path

from src.core.config import PROJECT_ROOT

from .catalog import settings


def export_skills(host: str) -> dict:
    relative = settings()["exports"].get(host)
    if not relative:
        raise ValueError("该宿主CLI的项目Skill发现目录尚未核验；可直接使用egs/skills.py，不套用IDE目录")
    root = (PROJECT_ROOT / relative).resolve()
    if not root.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError("Skill导出目录越界")
    manifest_path = root / ".quant-manifest.json"
    if not manifest_path.resolve().is_relative_to(root):
        raise ValueError("Skill导出清单路径越界")
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    if previous and previous.get("source") != "src/skills":
        raise ValueError("已有导出清单不属于本项目")
    changes, hashes = [], {}
    for skill in settings()["workflows"]:
        source = PROJECT_ROOT / "src/skills" / skill
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            key = (Path(skill) / path.relative_to(source)).as_posix()
            target = root / key
            if not target.resolve().is_relative_to(root) or not path.resolve().is_relative_to(PROJECT_ROOT.resolve()):
                raise ValueError("Skill文件路径越界")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if target.is_file():
                existing = hashlib.sha256(target.read_bytes()).hexdigest()
                if existing not in {digest, previous.get("files", {}).get(key)}:
                    raise ValueError("目标有不属于本生成器的同名内容：" + key)
            changes.append((path, target))
            hashes[key] = digest
    for source, target in changes:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    manifest = {"source": "src/skills", "host": host, "files": hashes, "deleted_files": []}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"host": host, "directory": str(root), "skills": len(settings()["workflows"]), "files": len(hashes)}
