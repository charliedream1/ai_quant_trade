"""File storage under the project data directory."""

import re
from pathlib import Path

from .config import get_settings
from .exceptions import BusinessError, ErrorCode


class FileStorage:
    def __init__(self, base_dir: Path | None = None) -> None:
        settings = get_settings()
        self.base_dir = base_dir or settings.data_dir
        self.document_dir = settings.document_storage_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.document_dir.mkdir(parents=True, exist_ok=True)

    def ensure_dirs(self) -> None:
        for rel in [
            "strategies/upload",
            "strategies/cli_generated",
            "knowledge/notes",
            "knowledge/papers",
            "knowledge/reports",
            "reports/backtest",
            "reports/model",
            "logs",
            "backup",
        ]:
            (self.base_dir / rel).mkdir(parents=True, exist_ok=True)
        self.document_dir.mkdir(parents=True, exist_ok=True)

    def safe_filename(self, name: str, suffix: str = "") -> str:
        clean = re.sub(r"[^\w\u4e00-\u9fff\-.]+", "_", name).strip("._")
        clean = clean[:80] or "untitled"
        if suffix and not clean.endswith(suffix):
            clean += suffix
        return clean

    def resolve(self, relative_path: str) -> Path:
        path = Path(str(relative_path or ""))
        target = path.resolve() if path.is_absolute() else (self.base_dir / path).resolve()
        base = self.base_dir.resolve()
        document_base = self.document_dir.resolve()
        if not (_is_under(target, base) or _is_under(target, document_base)):
            raise BusinessError(ErrorCode.STORAGE_ERROR, "文件路径越界")
        return target

    def document_path(self, filename: str) -> str:
        target = (self.document_dir / filename).resolve()
        if not _is_under(target, self.document_dir.resolve()):
            raise BusinessError(ErrorCode.STORAGE_ERROR, "文件路径越界")
        try:
            return target.relative_to(self.base_dir.resolve()).as_posix()
        except ValueError:
            return target.as_posix()

    def write_text(self, relative_path: str, content: str) -> str:
        target = self.resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return relative_path.replace("\\", "/")

    def read_text(self, relative_path: str) -> str:
        target = self.resolve(relative_path)
        if not target.exists():
            raise BusinessError(ErrorCode.NOT_FOUND, "文件不存在")
        return target.read_text(encoding="utf-8")

    def delete(self, relative_path: str) -> None:
        target = self.resolve(relative_path)
        if target.exists():
            target.unlink()


def _is_under(target: Path, base: Path) -> bool:
    return target == base or base in target.parents
