"""Bounded batch IPC to the project-local image decoder; no Pillow import in Web."""

import base64
import json
import os
import subprocess
from pathlib import Path

import yaml

from src.core.config import PROJECT_ROOT
from src.core.exceptions import BusinessError, ErrorCode
from src.core.process_env import process_environment


def validate_images(images: list[tuple[str, bytes]]) -> dict[str, str]:
    if not images:
        return {}
    config = yaml.safe_load((PROJECT_ROOT / "egs/image_validation.yaml").read_text(encoding="utf-8"))
    root = (PROJECT_ROOT / config["environment"]).resolve()
    if not root.is_relative_to(PROJECT_ROOT):
        raise BusinessError(ErrorCode.INVALID_PARAM, "图片校验环境必须在项目目录内")
    python = root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        raise BusinessError(ErrorCode.INVALID_PARAM, "缺少独立图片校验环境，请按安装文档创建 .venv-image-secure")
    payload = {
        "limits": config,
        "images": [{"name": name, "content": base64.b64encode(data).decode("ascii")} for name, data in images],
    }
    try:
        result = subprocess.run(
            [str(python), "-I", "-B", "-X", "utf8", str(Path(__file__).with_name("image_worker.py"))],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=config["timeout_seconds"],
            check=True,
            env=process_environment("image"),
        )
        report = json.loads(result.stdout)
        rows = report["images"]
        if report["pillow"] != config["pillow_version"] or len(rows) != len(images):
            raise ValueError("图片校验协议不一致")
        for (name, _), row in zip(images, rows, strict=True):
            if row.get("name") != name:
                raise ValueError("图片校验顺序不一致")
            if row.get("error"):
                raise BusinessError(ErrorCode.INVALID_PARAM, f"图片 {Path(name).name} 校验失败：{row['error']}")
        return {row["name"]: row["mime"] for row in rows}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        raise BusinessError(ErrorCode.INVALID_PARAM, "图片校验服务失败或超时，未发送模型请求") from exc
