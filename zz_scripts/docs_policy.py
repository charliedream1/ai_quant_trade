"""Shared publication and language scope for maintained repository documentation."""

from functools import lru_cache
from pathlib import Path

import pathspec
import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


@lru_cache(maxsize=1)
def configuration():
    # BaseLoader reads policy values without evaluating Material's Python-name tags.
    return yaml.load(  # nosec B506
        (ROOT / "mkdocs.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )


def published(path: Path) -> bool:
    relative = path.relative_to(DOCS).as_posix()
    if path.is_dir():
        relative += "/"
    rules = configuration().get("exclude_docs", "").splitlines()
    return not pathspec.PathSpec.from_lines("gitwildmatch", rules).match_file(relative)


def chinese_fallback(relative: str) -> bool:
    roots = configuration().get("extra", {}).get("i18n_fallback_roots", [])
    return any(relative == root or relative.startswith(root.rstrip("/") + "/") for root in roots)
