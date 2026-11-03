"""Mount the generated help site into FastAPI."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.core.config import Settings, get_settings
from src.core.logger import get_logger

from .builder import HelpDocsStatus, ensure_help_docs_site

log = get_logger("help_docs")


def mount_help_docs(app: FastAPI, settings: Settings | None = None) -> HelpDocsStatus:
    """Prepare and mount the static help documentation site."""

    cfg = settings or get_settings()
    status = ensure_help_docs_site(cfg)
    app.mount(
        cfg.help_docs_mount_path,
        StaticFiles(directory=str(status.site_dir), html=True),
        name="help-docs",
    )
    log.info(
        "help docs mounted | path={}/ site_dir={} built={} fallback={}",
        cfg.help_docs_mount_path,
        status.site_dir,
        status.built,
        status.fallback,
    )
    return status
