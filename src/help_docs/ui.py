"""Small UI helpers for embedding the MkDocs help site."""

from __future__ import annotations

from html import escape

from src.core.config import get_settings


def help_docs_iframe_html(mount_path: str | None = None) -> str:
    """Return the Gradio HTML used by the Help tab."""

    path = _normalize_mount_path(mount_path or get_settings().help_docs_mount_path)
    escaped_path = escape(f"{path}/", quote=True)
    return (
        "<div class='help-docs-shell'>"
        "<div class='help-docs-toolbar'>"
        f"<a href='{escaped_path}' target='_blank' rel='noopener noreferrer'>新窗口打开</a>"
        "</div>"
        f"<iframe class='help-docs-frame' src='{escaped_path}' title='AIQuant智投帮助文档' loading='lazy'></iframe>"
        "</div>"
    )


def _normalize_mount_path(value: str) -> str:
    text = str(value or "/help-docs").strip()
    if not text.startswith("/"):
        text = f"/{text}"
    return text.rstrip("/") or "/help-docs"
