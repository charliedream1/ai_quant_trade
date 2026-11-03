"""Small viewer host; document bytes and edit rights are loaded through file-ID APIs."""

from html import escape
from pathlib import Path
from uuid import uuid4

from src.core.config import get_settings


def launcher(record: dict) -> str:
    url = f"{get_settings().api_prefix}/file-previews/{record['id']}/view"
    return (
        f'<a href="{escape(url, quote=True)}" data-preview-auto="{uuid4().hex}" '
        f'class="workspace-shortcut">阅读：{escape(record["name"])}'
        f" · {'Markdown可编辑' if record['editable'] else '只读'}</a>"
    )


def viewer_html(identifier: str) -> str:
    root = Path(__file__).resolve().parents[1] / "frontend/assets/file_viewer"
    source = (root / "reader.html").read_text(encoding="utf-8")
    return source.replace("__FILE_ID__", escape(identifier, quote=True)).replace(
        "__API_PREFIX__", escape(get_settings().api_prefix, quote=True)
    )
