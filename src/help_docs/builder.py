"""Build the local MkDocs help site."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from src.core.config import Settings, get_settings
from src.core.logger import get_logger

log = get_logger("help_docs")


@dataclass(frozen=True)
class HelpDocsStatus:
    """Result of preparing the static help site."""

    mounted: bool
    built: bool
    fallback: bool
    source_dir: Path
    site_dir: Path
    index_path: Path
    message: str


def ensure_help_docs_site(settings: Settings | None = None) -> HelpDocsStatus:
    """Build or refresh the MkDocs site, falling back to a small static page on failure."""

    cfg = settings or get_settings()
    source_dir = cfg.project_root / "docs"
    config_path = cfg.project_root / "mkdocs.yml"
    platform_config = cfg.project_root / "mkdocs.platform.yml"
    if platform_config.is_file():
        config_path = platform_config
    site_dir = cfg.help_docs_site_dir
    index_path = site_dir / "index.html"
    if not source_dir.exists() or not config_path.exists():
        message = "help docs source missing"
        log.warning(
            "help docs source missing | source_dir={} config_path={} site_dir={}",
            source_dir,
            config_path,
            site_dir,
        )
        _write_fallback_index(site_dir, message)
        return HelpDocsStatus(True, False, True, source_dir, site_dir, index_path, message)

    if not cfg.help_docs_auto_build:
        if not index_path.exists():
            message = "help docs auto build disabled"
            log.info("help docs auto build disabled | site_dir={}", site_dir)
            _write_fallback_index(site_dir, message)
            return HelpDocsStatus(True, False, True, source_dir, site_dir, index_path, message)
        message = "help docs reused existing site"
        log.info("help docs reused existing site | site_dir={}", site_dir)
        return HelpDocsStatus(True, False, False, source_dir, site_dir, index_path, message)

    if not _needs_rebuild(source_dir, config_path, index_path):
        message = "help docs already current"
        log.info("help docs already current | site_dir={}", site_dir)
        return HelpDocsStatus(True, False, False, source_dir, site_dir, index_path, message)

    try:
        _run_mkdocs_build(config_path, site_dir)
    except (OSError, subprocess.SubprocessError) as exc:
        message = f"help docs build failed: {exc.__class__.__name__}"
        log.warning(
            "help docs build failed | config_path={} site_dir={} error_type={} reason={}",
            config_path,
            site_dir,
            exc.__class__.__name__,
            exc,
        )
        _write_fallback_index(site_dir, message)
        return HelpDocsStatus(True, False, True, source_dir, site_dir, index_path, message)

    message = "help docs built"
    log.info("help docs built | source_dir={} site_dir={}", source_dir, site_dir)
    return HelpDocsStatus(True, True, False, source_dir, site_dir, index_path, message)


def _needs_rebuild(source_dir: Path, config_path: Path, index_path: Path) -> bool:
    if not index_path.exists():
        return True
    site_mtime = index_path.stat().st_mtime
    # Track published content and images without scanning historical audit assets.
    try:
        configuration = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        roots = configuration["extra"]["help_source_roots"]
        if not isinstance(roots, list) or not roots:
            return True
    except (OSError, KeyError, TypeError, yaml.YAMLError):
        return True
    candidates = [config_path, source_dir / "index.md"]
    for name in roots:
        root = (source_dir / str(name)).resolve()
        if not root.is_relative_to(source_dir.resolve()):
            return True
        candidates.extend(path for path in root.rglob("*") if path.is_file())
    return any(path.stat().st_mtime > site_mtime for path in candidates if path.exists())


def _run_mkdocs_build(config_path: Path, site_dir: Path) -> None:
    site_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "mkdocs",
        "build",
        "--clean",
        "--config-file",
        str(config_path),
        "--site-dir",
        str(site_dir),
    ]
    started = subprocess.run(
        command,
        cwd=str(config_path.parent),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if started.stdout.strip():
        log.debug("help docs mkdocs stdout | output={}", started.stdout.strip())
    if started.stderr.strip():
        log.debug("help docs mkdocs stderr | output={}", started.stderr.strip())
    if started.returncode != 0:
        raise subprocess.CalledProcessError(started.returncode, command, started.stdout, started.stderr)


def _write_fallback_index(site_dir: Path, message: str) -> None:
    site_dir.mkdir(parents=True, exist_ok=True)
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AIQuant智投帮助文档</title>
  <style>
    body {{ font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif; margin: 32px; color: #12304a; }}
    main {{ max-width: 760px; }}
    a {{ color: #2563eb; }}
  </style>
</head>
<body>
  <main>
    <h1>AIQuant智投帮助文档</h1>
    <p>帮助站点暂未完成构建：{message}</p>
    <p>请检查项目根目录的 <code>mkdocs.yml</code> 与 <code>docs/usage/</code>、<code>docs/principles/</code> 文档源。</p>
  </main>
</body>
</html>
"""
    (site_dir / "index.html").write_text(html, encoding="utf-8")
