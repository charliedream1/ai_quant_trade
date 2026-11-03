"""Bounded, deduplicated Office-to-PDF jobs with an isolated LibreOffice profile."""

import json
import os
import shutil
import signal
import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import RLock
from uuid import uuid4

from dotenv import dotenv_values
from loguru import logger
from pypdf import PdfReader

from src.core.config import PROJECT_ROOT
from src.core.exceptions import BusinessError, ErrorCode
from src.core.process_env import process_environment

from .access import bounded_read, compact_path
from .config import digest, preview_config
from .store import PreviewStore

_LOCK = RLock()
_EXECUTOR: ThreadPoolExecutor | None = None
_JOBS: dict[str, Future] = {}


def _profile_uri(path: Path) -> str:
    return compact_path(path).as_uri()


def executable() -> str:
    config = preview_config()["converter"]
    if config["backend"] != "libreoffice":
        raise BusinessError(ErrorCode.INVALID_PARAM, "当前文件预览仅接入LibreOffice转换器")
    candidate = (
        os.environ.get("ALL_IN_ONE_PREVIEW_OFFICE")
        or dotenv_values(PROJECT_ROOT / ".env").get("ALL_IN_ONE_PREVIEW_OFFICE")
        or config["windows_executable" if os.name == "nt" else "linux_executable"]
    )
    path = Path(candidate)
    if not path.is_absolute() and (PROJECT_ROOT / path).is_file():
        path = PROJECT_ROOT / path
    result = str(path) if path.is_file() else shutil.which(candidate)
    if not result:
        raise BusinessError(ErrorCode.INVALID_PARAM, "Office转换器未配置，请按文件阅读安装指南配置LibreOffice")
    return result


def _stop(process: subprocess.Popen[bytes]) -> None:
    if sys.platform == "win32":
        taskkill = shutil.which("taskkill")
        if taskkill:
            subprocess.run([taskkill, "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
        else:
            process.kill()
    else:
        os.killpg(process.pid, signal.SIGKILL)


def _convert(row: dict, cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    working_root = (PROJECT_ROOT / preview_config()["converter"]["work_directory"]).resolve()
    if not working_root.is_relative_to(PROJECT_ROOT.resolve()):
        raise BusinessError(ErrorCode.INVALID_PARAM, "转换工作区必须位于项目内")
    working = working_root / uuid4().hex[:16]
    working.mkdir(parents=True)
    store = PreviewStore()
    source = store.path(store.read(row["id"]))
    # Freeze the exact bytes whose hash selected this conversion cache.
    content = bounded_read(source)
    if digest(content) != row["revision"]:
        raise BusinessError(ErrorCode.CONSTRAINT_CONFLICT, "文件已变化，请重新打开后预览")
    original = working / ("document" + source.suffix.lower())
    original.write_bytes(content)
    profile = working / "profile"
    (profile / "user").mkdir(parents=True, exist_ok=True)
    template = PROJECT_ROOT / preview_config()["converter"]["profile_template"]
    shutil.copyfile(template, profile / "user/registrymodifications.xcu")
    command = [
        executable(),
        "-env:UserInstallation=" + _profile_uri(profile),
        "--headless",
        "--nologo",
        "--nodefault",
        "--norestore",
        "--convert-to",
        "pdf",
        "--outdir",
        str(working),
        str(original),
    ]
    creationflags = (
        (getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        if sys.platform == "win32"
        else 0
    )
    logger.info("Office预览转换开始 | file={} cache={}", row["id"], cache.name)
    with subprocess.Popen[bytes](
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
        env=process_environment("document"),
        start_new_session=os.name != "nt",
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=preview_config()["limits"]["conversion_timeout_seconds"])
        except subprocess.TimeoutExpired as exc:
            _stop(process)
            process.communicate()
            raise BusinessError(ErrorCode.DATA_SOURCE_ERROR, "Office转换超时，已停止本次转换进程") from exc
    (cache / "conversion.log").write_bytes(stdout + b"\n" + stderr)
    result = working / "document.pdf"
    if process.returncode or not result.is_file():
        logger.error("Office转换未生成PDF | file={} returncode={} work={}", row["id"], process.returncode, working)
        raise BusinessError(ErrorCode.PARSE_ERROR, "Office转换失败，文件可能损坏、加密或格式不受支持；原件仍可下载")
    if result.stat().st_size > preview_config()["limits"]["max_pdf_bytes"]:
        raise BusinessError(ErrorCode.INVALID_PARAM, "转换PDF超过预览资源上限")
    reader = PdfReader(result)
    if not reader.pages:
        raise BusinessError(ErrorCode.PARSE_ERROR, "转换PDF没有可阅读页面")
    cached = cache / "document.pdf"
    shutil.copyfile(result, cached)
    (cache / "complete.json").write_text(
        json.dumps({"sha256": digest(result.read_bytes()), "pages": len(reader.pages)}), encoding="utf-8"
    )
    logger.info("Office预览转换完成 | file={} bytes={}", row["id"], result.stat().st_size)
    return cached


def request_pdf(row: dict) -> dict:
    global _EXECUTOR
    settings = preview_config()
    signature = json.dumps(settings["converter"], sort_keys=True).encode()
    binary = Path(executable())
    signature += (PROJECT_ROOT / settings["converter"]["profile_template"]).read_bytes()
    key = digest((row["revision"] + str(binary) + str(binary.stat().st_mtime_ns)).encode() + signature)
    cache = PreviewStore().root / "converted" / key
    result = cache / "document.pdf"
    with _LOCK:
        job_key = str(cache)
        job = _JOBS.get(job_key)
        if job is not None and not job.done():
            return {"status": "running" if job.running() else "queued", "cache_key": key}
        if result.is_file() and (cache / "complete.json").is_file():
            stamp = json.loads((cache / "complete.json").read_text(encoding="utf-8"))
            if digest(result.read_bytes()) == stamp["sha256"]:
                return {"status": "completed", "cache_key": key, "path": str(result), "cached": True}
        if job is not None:
            try:
                job.result()
            except Exception as exc:
                return {"status": "failed", "error": str(exc), "cache_key": key}
        if _EXECUTOR is None:
            _EXECUTOR = ThreadPoolExecutor(
                max_workers=settings["limits"]["workers"], thread_name_prefix="office-preview"
            )
        if sum(not future.done() for future in _JOBS.values()) >= settings["limits"]["max_pending_conversions"]:
            raise BusinessError(ErrorCode.CONSTRAINT_CONFLICT, "Office转换队列已满，请稍后重试")
        _JOBS[job_key] = _EXECUTOR.submit(_convert, dict(row), cache)
    return {"status": "running", "cache_key": key}


def shutdown() -> None:
    global _EXECUTOR
    with _LOCK:
        executor, _EXECUTOR = _EXECUTOR, None
    if executor is not None:
        executor.shutdown(wait=True, cancel_futures=True)
    with _LOCK:
        _JOBS.clear()


def text_pdf(row: dict) -> Path:
    """Wait for the same bounded conversion job used by the read-only viewer."""
    state = request_pdf(row)
    if state["status"] == "completed":
        return Path(state["path"])
    if state["status"] == "failed":
        raise BusinessError(ErrorCode.PARSE_ERROR, state["error"])
    cache = PreviewStore().root / "converted" / state["cache_key"]
    with _LOCK:
        future = _JOBS[str(cache)]
    return Path(future.result())
