# -*- coding: utf-8 -*-
"""
Pre-flight check for mkdocs build. Run before `mkdocs build` in CI and
locally; exit 1 if any check fails.

Pure stdlib — no mkdocs / yaml import required for parsing yaml nav.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
MKDOCS_YML = REPO_ROOT / "mkdocs.yml"
INDEX_MD = DOCS / "index.md"

MARKER_PAIRS: list[tuple[str, str, str, str]] = [
    ("mkdocs.yml", str(MKDOCS_YML.relative_to(REPO_ROOT)),
     "# >>> AUTO-NAV-START", "# <<< AUTO-NAV-END"),
    ("docs/index.md", str(INDEX_MD.relative_to(REPO_ROOT)),
     "<!-- >>> AUTO-INDEX-START", "<!-- <<< AUTO-INDEX-END"),
]


def _parse_simple_yaml_nav(text: str) -> list[tuple[int, str]]:
    """Crude parser: extract `nav:`-block file paths as `(line, path)` pairs.

    Only handles the subset our mkdocs.yml uses (relative .md paths,
    including CJK characters in subdirectory names).
    """
    # Match ASCII path chars + CJK Unified Ideographs + SPACE (directory
    # names like "教程 FAQ" contain a space) + extension .md.
    path_re = re.compile(r"[A-Za-z0-9_./\-\u4e00-\u9fff ]+\.md")
    out: list[tuple[int, str]] = []
    in_nav = False
    for i, line in enumerate(text.splitlines(), start=1):
        if line.startswith("nav:"):
            in_nav = True
            continue
        if in_nav:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Heuristic: any token ending in .md that isn't a section header.
            for tok in path_re.findall(stripped):
                # Strip leading/trailing whitespace so that directory names
                # containing spaces (e.g. "教程 FAQ") resolve correctly.
                out.append((i, tok.strip()))
            # If indentation returns to column 0 on a non-nav key, nav ended.
            if line and not line.startswith((" ", "\t")) and ":" in stripped \
                    and not stripped.startswith("-"):
                if re.match(r"^[a-z_]+:", stripped):
                    in_nav = False
    return out


def check_mkdocs_yml_parseable() -> list[str]:
    if not MKDOCS_YML.is_file():
        return [f"{MKDOCS_YML}: not found"]
    try:
        text = MKDOCS_YML.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{MKDOCS_YML}: read failed: {e}"]
    # Skip full yaml parse if PyYAML missing; use the simple parser instead.
    try:
        import yaml  # noqa: F401
        try:
            # mkdocs.yml uses `!!python/name:material.extensions.emoji.twemoji`
            # which safe_load rejects. Use BaseLoader to accept custom tags
            # without constructing Python objects.
            yaml.load(text, Loader=yaml.BaseLoader)
        except Exception as e:
            return [f"{MKDOCS_YML}: yaml parse failed: {e}"]
    except ImportError:
        pass
    return []


def check_nav_files_exist() -> list[str]:
    text = MKDOCS_YML.read_text(encoding="utf-8")
    errors: list[str] = []
    for line_no, path in _parse_simple_yaml_nav(text):
        if path.startswith(("http://", "https://", "mailto:")):
            continue
        # nav paths are relative to docs_dir = docs/.
        full = DOCS / path
        if not full.is_file():
            errors.append(f"{MKDOCS_YML}:{line_no}: nav file missing: {path}")
    return errors


def check_auto_markers() -> list[str]:
    errors: list[str] = []
    for label, path, start, end in MARKER_PAIRS:
        full = REPO_ROOT / path
        if not full.is_file():
            errors.append(f"{label}: file missing: {path}")
            continue
        text = full.read_text(encoding="utf-8")
        has_start = start in text
        has_end = end in text
        if has_start != has_end:
            errors.append(
                f"{label}: only one of the pair found "
                f"(start={has_start}, end={has_end})"
            )
    return errors


def check_index_has_language_switch() -> list[str]:
    if not INDEX_MD.is_file():
        return [f"{INDEX_MD}: not found"]
    text = INDEX_MD.read_text(encoding="utf-8")
    errors: list[str] = []
    if "language-switch" not in text:
        errors.append(f"{INDEX_MD}: missing <div class=\"language-switch\">")
    # Two language blocks must exist.
    if 'class="lang-en"' not in text:
        errors.append(f"{INDEX_MD}: missing .lang-en block")
    if 'class="lang-zh"' not in text:
        errors.append(f"{INDEX_MD}: missing .lang-zh block")
    return errors


def check_extra_assets_listed() -> list[str]:
    """All *.css / *.js files in docs/stylesheets/ and docs/javascripts/
    must appear in mkdocs.yml's extra_css / extra_javascript."""
    text = MKDOCS_YML.read_text(encoding="utf-8")
    errors: list[str] = []

    css_dir = DOCS / "stylesheets"
    if css_dir.is_dir():
        for css in css_dir.rglob("*.css"):
            rel = css.relative_to(DOCS).as_posix()
            if rel not in text:
                errors.append(
                    f"{MKDOCS_YML}: CSS file not in extra_css: {rel}"
                )

    js_dir = DOCS / "javascripts"
    if js_dir.is_dir():
        for js in js_dir.rglob("*.js"):
            rel = js.relative_to(DOCS).as_posix()
            if rel not in text:
                errors.append(
                    f"{MKDOCS_YML}: JS file not in extra_javascript: {rel}"
                )
    return errors


def main() -> None:
    all_errors: list[tuple[str, list[str]]] = [
        ("mkdocs.yml parseable", check_mkdocs_yml_parseable()),
        ("nav files exist", check_nav_files_exist()),
        ("auto markers", check_auto_markers()),
        ("index has language switch", check_index_has_language_switch()),
        ("extra_css / extra_javascript up to date",
         check_extra_assets_listed()),
    ]

    total = 0
    for name, errs in all_errors:
        if errs:
            total += len(errs)
            print(f"\n[check_docs_build] FAIL: {name}")
            for e in errs:
                print(f"  - {e}")

    if total:
        print(f"\n[check_docs_build] {total} issue(s) found. Aborting.")
        sys.exit(1)
    print(f"[check_docs_build] OK — all {len(all_errors)} checks passed.")


if __name__ == "__main__":
    main()
