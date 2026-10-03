# -*- coding: utf-8 -*-
"""
Pre-flight check for the MkDocs documentation site.

The published site is intentionally scoped to docs/ and is bilingual:
- Chinese source pages use the normal .md filename.
- English pages use the .en.md suffix.
- Language switching is handled by mkdocs-static-i18n at build time, not by a
  runtime JavaScript translator.
- fallback_to_default is enabled for shared static assets, while this script
  enforces that every publishable Markdown source has an English translation.
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
    """Extract Markdown file paths from the subset of mkdocs.yml nav we use."""
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
            for tok in path_re.findall(stripped):
                out.append((i, tok.strip()))
            if line and not line.startswith((" ", "\t")) and ":" in stripped \
                    and not stripped.startswith("-"):
                if re.match(r"^[a-z_]+:", stripped):
                    in_nav = False
    return out


def _localized_markdown_path(path: str, locale: str) -> Path:
    src = DOCS / path
    return src.with_name(f"{src.stem}.{locale}{src.suffix}")


def check_mkdocs_yml_parseable() -> list[str]:
    if not MKDOCS_YML.is_file():
        return [f"{MKDOCS_YML}: not found"]
    try:
        text = MKDOCS_YML.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{MKDOCS_YML}: read failed: {e}"]
    try:
        import yaml  # noqa: F401
        try:
            # mkdocs.yml uses !!python/name for pymdownx emoji support.
            yaml.load(text, Loader=yaml.BaseLoader)
        except Exception as e:
            return [f"{MKDOCS_YML}: yaml parse failed: {e}"]
    except ImportError:
        pass
    return []


def check_i18n_config() -> list[str]:
    text = MKDOCS_YML.read_text(encoding="utf-8")
    required = [
        "- i18n:",
        "docs_structure: suffix",
        "fallback_to_default: true",
        "reconfigure_material: true",
        "reconfigure_search: true",
        "locale: zh",
        "locale: en",
        "nav_translations:",
    ]
    errors = [
        f"{MKDOCS_YML}: missing i18n config entry: {item}"
        for item in required
        if item not in text
    ]
    legacy = [
        "language-switch.js",
        "language-switch.css",
    ]
    for item in legacy:
        if item in text:
            errors.append(
                f"{MKDOCS_YML}: legacy runtime language switch still listed: {item}"
            )
    return errors


def check_nav_files_exist() -> list[str]:
    text = MKDOCS_YML.read_text(encoding="utf-8")
    errors: list[str] = []
    for line_no, path in _parse_simple_yaml_nav(text):
        if path.startswith(("http://", "https://", "mailto:")):
            continue
        full = DOCS / path
        if not full.is_file():
            errors.append(f"{MKDOCS_YML}:{line_no}: nav file missing: {path}")
    return errors


def check_english_nav_translations_exist() -> list[str]:
    text = MKDOCS_YML.read_text(encoding="utf-8")
    errors: list[str] = []
    for line_no, path in _parse_simple_yaml_nav(text):
        if path.startswith(("http://", "https://", "mailto:")):
            continue
        translated = _localized_markdown_path(path, "en")
        if not translated.is_file():
            rel = translated.relative_to(REPO_ROOT).as_posix()
            errors.append(
                f"{MKDOCS_YML}:{line_no}: English translation missing: {rel}"
            )
    return errors


def iter_publishable_default_markdown() -> list[Path]:
    files: list[Path] = []
    for path in DOCS.rglob("*.md"):
        rel = path.relative_to(DOCS).as_posix()
        if rel == "intro.md" or rel.startswith("snippets/"):
            continue
        if path.stem.endswith(".en"):
            continue
        files.append(path)
    return sorted(files)


def check_all_publishable_markdown_translated() -> list[str]:
    errors: list[str] = []
    for path in iter_publishable_default_markdown():
        translated = path.with_name(f"{path.stem}.en{path.suffix}")
        if not translated.is_file():
            rel = translated.relative_to(REPO_ROOT).as_posix()
            errors.append(f"English translation missing: {rel}")
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
                f"{label}: only one of the marker pair was found "
                f"(start={has_start}, end={has_end})"
            )
    return errors


def check_no_legacy_runtime_language_switch() -> list[str]:
    errors: list[str] = []
    legacy_files = [
        DOCS / "javascripts" / "language-switch.js",
        DOCS / "stylesheets" / "language-switch.css",
    ]
    for path in legacy_files:
        if path.exists():
            rel = path.relative_to(REPO_ROOT).as_posix()
            errors.append(f"{rel}: remove legacy runtime language switch asset")

    if INDEX_MD.is_file():
        text = INDEX_MD.read_text(encoding="utf-8")
        for token in ("lang-en", "lang-zh", "language-switch"):
            if token in text:
                errors.append(
                    f"{INDEX_MD.relative_to(REPO_ROOT).as_posix()}: "
                    f"legacy language block token still present: {token}"
                )
    return errors


def check_no_dot_prefixed_docs_dirs() -> list[str]:
    errors: list[str] = []
    if not DOCS.is_dir():
        return errors
    for path in DOCS.rglob("*"):
        if path.is_dir() and path.name.startswith("."):
            rel = path.relative_to(REPO_ROOT).as_posix()
            errors.append(f"{rel}: dot-prefixed docs directories are not publishable")
    for path in DOCS.rglob("*.md"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "](." in text:
            errors.append(f"{rel}: contains dot-prefixed relative link")
    return errors


def check_extra_assets_listed() -> list[str]:
    """All CSS/JS files under docs assets must be listed in mkdocs.yml."""
    text = MKDOCS_YML.read_text(encoding="utf-8")
    errors: list[str] = []

    css_dir = DOCS / "stylesheets"
    if css_dir.is_dir():
        for css in css_dir.rglob("*.css"):
            rel = css.relative_to(DOCS).as_posix()
            if rel not in text:
                errors.append(f"{MKDOCS_YML}: CSS file not in extra_css: {rel}")

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
        ("i18n config", check_i18n_config()),
        ("nav files exist", check_nav_files_exist()),
        ("English nav translations exist", check_english_nav_translations_exist()),
        ("all publishable Markdown translated", check_all_publishable_markdown_translated()),
        ("auto markers", check_auto_markers()),
        ("no legacy runtime language switch", check_no_legacy_runtime_language_switch()),
        ("no dot-prefixed docs asset dirs", check_no_dot_prefixed_docs_dirs()),
        ("extra_css / extra_javascript up to date", check_extra_assets_listed()),
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
    print(f"[check_docs_build] OK - all {len(all_errors)} checks passed.")


if __name__ == "__main__":
    main()
