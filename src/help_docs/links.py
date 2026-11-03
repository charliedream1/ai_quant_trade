"""Resolve handbook links for Markdown displayed outside the static help site."""

import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from src.core.config import Settings


def handbook_markdown(content: str, source: Path, settings: Settings) -> str:
    """Keep tutorial images and cross-links usable in the learning reader."""
    docs = (settings.project_root / "docs").resolve()

    def replace(match: re.Match[str]) -> str:
        prefix, target, suffix = match.groups()
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
            return match.group(0)
        resolved = (source.parent / unquote(parsed.path)).resolve()
        if not resolved.is_relative_to(docs):
            return match.group(0)
        relative = resolved.relative_to(docs)
        if not relative.parts or relative.parts[0] not in {"usage", "principles"}:
            return match.group(0)
        if relative.suffix == ".md":
            relative = relative.parent if relative.name == "README.md" else relative.with_suffix("")
            route = relative.as_posix().rstrip("/") + "/"
        else:
            route = relative.as_posix()
        url = settings.help_docs_mount_path.rstrip("/") + "/" + quote(route, safe="/")
        if parsed.query:
            url += "?" + parsed.query
        if parsed.fragment:
            url += "#" + parsed.fragment
        return prefix + url + suffix

    return re.sub(r"(!?\[[^\]]*\]\()([^\s)]+)(\))", replace, content)
