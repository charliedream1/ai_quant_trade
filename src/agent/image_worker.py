"""Isolated Pillow worker. Stdout is a JSON protocol, never a model response."""

import base64
import io
import json
import sys
import warnings
from pathlib import Path
from typing import cast

import yaml
from PIL import Image, UnidentifiedImageError, __version__


def validate(item: dict, limits: dict) -> dict:
    name = item["name"]
    try:
        expected = limits["formats"][Path(name).suffix.lower()]
        content = base64.b64decode(item["content"], validate=True)
        Image.MAX_IMAGE_PIXELS = limits["max_pixels"]
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content), formats=[expected["format"]]) as image:
                width, height = image.size
                if width * height > limits["max_pixels"]:
                    raise ValueError("像素数量超过上限")
                if getattr(image, "n_frames", 1) > limits["max_frames"]:
                    raise ValueError("帧数超过上限，不接受动画图片")
                if width * height * max(len(image.getbands()), 4) > limits["max_decoded_bytes"]:
                    raise ValueError("解码内存超过上限")
                image.verify()
            # verify alone does not fully decode JPEG/WebP; reopen and load all accepted pixels.
            with Image.open(io.BytesIO(content), formats=[expected["format"]]) as image:
                image.load()
        return {"name": name, "mime": expected["mime"], "width": width, "height": height}
    except UnidentifiedImageError:
        return {"name": name, "error": "格式不符，文件内容不是该后缀声明的图片"}
    except (OSError, SyntaxError):
        return {"name": name, "error": "图片内容损坏或不完整，请重新导出后上传"}
    except (ValueError, KeyError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        return {"name": name, "error": f"格式不符、损坏或超限：{exc}"}


def main() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        cast(io.TextIOWrapper, stream).reconfigure(encoding="utf-8")
    # -I ensures package imports come from this interpreter, independent of the Web sys.path.
    project = Path(__file__).resolve().parents[2]
    config = yaml.safe_load((project / "egs/config/models/image_validation.yaml").read_text(encoding="utf-8"))
    prefix = (project / config["environment"]).resolve()
    cfg = prefix / "pyvenv.cfg"
    if Path(sys.prefix).resolve() != prefix or __version__ != config["pillow_version"] or not cfg.is_file():
        raise SystemExit("图片校验必须运行于项目独立 Pillow 13 环境")
    if "include-system-site-packages = true" in cfg.read_text(encoding="utf-8").lower():
        raise SystemExit("图片校验环境不得继承基础包")
    payload = json.load(sys.stdin)
    result = {"pillow": __version__, "images": [validate(item, config) for item in payload["images"]]}
    sys.stdout.write(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
