# -*- coding: utf-8 -*-
"""Fail CI when the MkDocs site reaches outside its intended source scope."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {".css", ".html", ".js", ".md", ".sh", ".yml", ".yaml"}


def iter_checked_files() -> list[Path]:
    files: list[Path] = []
    explicit = [
        REPO_ROOT / "mkdocs.yml",
        REPO_ROOT / ".github" / "workflows" / "docs-pages.yml",
        REPO_ROOT / ".cloudflare" / "scripts" / "build.sh",
    ]
    files.extend(path for path in explicit if path.is_file())

    docs_dir = REPO_ROOT / "docs"
    if docs_dir.is_dir():
        for path in docs_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel == "docs/intro.md" or rel.startswith("docs/snippets/"):
                continue
            files.append(path)
    return sorted(set(files))


def main() -> None:
    forbidden = [
        ("generated project pages", "_" + "projects"),
        ("old wrapper generator", "gen_project_" + "wrappers"),
        ("include outside docs", "../" + "snippets"),
        ("markdown include directive", "{%" + " include"),
        ("example directory reference", "egs" + "_"),
        ("example directory path", "egs" + "/"),
        ("example directory path", "egs" + "\\"),
        ("notes wrapper source", "ai_" + "notes"),
        ("unused include plugin", "include-" + "markdown"),
    ]

    errors: list[str] = []
    for path in iter_checked_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, term in forbidden:
            if term in text:
                errors.append(f"{rel}: contains {label}: {term!r}")

    if errors:
        print("[check_docs_publish_scope] FAIL")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print(f"[check_docs_publish_scope] OK - checked {len(iter_checked_files())} files")


if __name__ == "__main__":
    main()
