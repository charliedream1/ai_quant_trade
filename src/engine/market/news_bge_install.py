"""Operator-confirmed installation of an immutable BGE model into a local directory."""

import argparse
import hashlib
import os
import sys
from importlib.util import find_spec
from pathlib import Path
from uuid import uuid4

from filelock import FileLock

from src.core.env_file import save_env_value
from src.core.logger import get_logger

from .news_bge import config, local_vectors, model_directory

LOG = get_logger("market.news")


def verify(path, expected):
    if path.stat().st_size != expected["bytes"]:
        raise ValueError("Unexpected BGE artifact size")
    data = path.read_bytes()
    if len(data) != expected["bytes"]:
        raise ValueError("Unexpected BGE artifact size")
    if "sha256" in expected:
        valid = hashlib.sha256(data).hexdigest() == expected["sha256"]
    else:
        header = f"blob {len(data)}\0".encode("ascii")
        valid = hashlib.sha1(header + data, usedforsecurity=False).hexdigest() == expected["git_blob_sha1"]
    if not valid:
        raise ValueError("BGE artifact integrity check failed")


def _fetch(name, destination, cfg):
    from huggingface_hub import hf_hub_download

    hf_hub_download(
        repo_id=cfg["model"],
        revision=cfg["revision"],
        filename=name,
        local_dir=destination,
        cache_dir=destination / ".cache",
        endpoint="https://huggingface.co",
        token=False,
    )


def install(target, *, confirmed=False):
    if not confirmed:
        return False
    cfg = config()
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(target.parent / (target.name + ".lock"))):
        if target.exists():
            for name, expected in cfg["assets"].items():
                verify(target / name, expected)
            local_vectors(target, ["市场"])
            return True
        stage = target.parent / (target.name + ".pending-" + uuid4().hex)
        stage.mkdir()
        for name, expected in cfg["assets"].items():
            _fetch(name, stage, cfg)
            verify(stage / name, expected)
        local_vectors(stage, ["市场"])
        if target.exists():
            raise ValueError("BGE destination was created during installation")
        stage.rename(target)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, help="Model directory. Defaults to the configured runtime path.")
    parser.add_argument("--confirm-download", action="store_true", help="Explicit noninteractive download approval.")
    parser.add_argument(
        "--download-only", action="store_true", help="Verify the model without changing workspace settings."
    )
    args = parser.parse_args(argv)
    target = (args.target or model_directory()).expanduser().resolve()
    cfg = config()
    size = sum(asset["bytes"] for asset in cfg["assets"].values())
    LOG.info(
        "BGE download preview | source=https://huggingface.co/{} revision={} bytes={} target={}",
        cfg["model"],
        cfg["revision"],
        size,
        target,
    )
    allowed = args.confirm_download
    if not allowed and sys.stdin.isatty():
        prompt = "Download BGE? [y/N] " if args.download_only else "Download and activate BGE? [y/N] "
        try:
            allowed = input(prompt).strip().casefold() == "y"
        except (EOFError, KeyboardInterrupt):
            allowed = False
    if not allowed:
        LOG.info("BGE download skipped")
        return 0
    if any(find_spec(package) is None for package in ("onnxruntime", "tokenizers")):
        LOG.error("Install the news-bge runtime extra before downloading the model")
        return 1
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    try:
        install(target, confirmed=True)
        if not args.download_only:
            save_env_value("ALL_IN_ONE_NEWS_BGE_DIRECTORY", str(target))
            save_env_value("ALL_IN_ONE_NEWS_BGE_MODE", "local")
    except Exception as exc:
        LOG.error("BGE installation failed | error_type={}", type(exc).__name__)
        return 1
    LOG.info("BGE local model verified | workspace_settings_updated={}", not args.download_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
