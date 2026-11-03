"""Resolve file identities inside configured project and storage boundaries."""

import ctypes
import sys
from fnmatch import fnmatch
from pathlib import Path

from src.core.config import PROJECT_ROOT
from src.core.exceptions import BusinessError, ErrorCode

from .config import file_kind, preview_config


def compact_path(path: Path) -> Path:
    """Use the same Windows directory through its short alias, without relocating data."""
    if sys.platform == "win32" and path.exists():
        buffer = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer)):
            return Path(buffer.value)
    return path


def project_file(name: str) -> Path:
    root = PROJECT_ROOT.resolve()
    requested = Path(str(name))
    if requested.is_absolute() or ".." in requested.parts:
        raise BusinessError(ErrorCode.INVALID_PARAM, "请使用项目内相对文件路径")
    path = (root / requested).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise BusinessError(ErrorCode.NOT_FOUND, "项目文件不存在或路径越界")
    relative = path.relative_to(root)
    policy = preview_config()["project"]
    if relative.as_posix() not in policy["public_exceptions"]:
        if any(fnmatch(relative.as_posix(), pattern) for pattern in policy["blocked_relative_globs"]):
            raise BusinessError(ErrorCode.INVALID_PARAM, "此数据或私有配置只能通过对应业务入口读取")
        if (
            any(part in policy["blocked_parts"] or part.startswith(".venv") for part in relative.parts)
            or path.suffix.lower() in policy["blocked_suffixes"]
            or any(path.name.startswith(prefix) for prefix in policy["blocked_prefixes"])
        ):
            raise BusinessError(ErrorCode.INVALID_PARAM, "受保护的运行、密钥或缓存文件不可预览")
    file_kind(path.name)
    return path


def can_edit_project(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT.resolve()).as_posix()
    policy = preview_config()["project"]
    return (
        file_kind(path.name) == "markdown"
        and any(relative == item or relative.startswith(item.rstrip("/") + "/") for item in policy["editable_roots"])
        and not any(fnmatch(relative, pattern) for pattern in policy["readonly_markdown_globs"])
    )


def bounded_read(path: Path, *, text: bool = False) -> bytes:
    limits = preview_config()["limits"]
    maximum = int(limits["max_text_bytes"] if text else limits["max_bytes"])
    with compact_path(path).open("rb") as stream:
        content = stream.read(maximum + 1)
    if len(content) > maximum:
        raise BusinessError(ErrorCode.INVALID_PARAM, "文件超过预览配置大小上限")
    return content
