# -*- coding: utf-8 -*-
"""
mkdocs hook: rewrite dot-prefixed directory names to underscore-prefixed.

Reason
------
GitHub Pages / Cloudflare Pages refuse to serve files in directories whose
names begin with a dot (security: protects .git, .env, etc.). The repo uses
folders like ``.01_xxx_images/`` for organization, which silently breaks image
rendering on the deployed site.

mkdocs applies a default ``.*`` gitignore-style exclusion (see
``mkdocs.structure.files._default_exclude``), so any file inside a dot
directory is marked ``InclusionLevel.EXCLUDED`` and never reaches ``site/``.

Strategy
--------
We cannot rename dot directories on disk without polluting the repository.
Instead, in ``on_files`` we:

1. Detect every ``File`` whose ``src_uri`` contains a dot-prefixed path
   component (basename ``file.name`` is just the bare stem in mkdocs 1.6, so
   the detection must work on ``src_uri``).
2. For each such ``File`` (which is EXCLUDED by the default ``.*`` rule):
   * read its bytes (markdown text or binary media) from disk,
   * create a new in-memory ``File`` whose ``src_uri`` is the dot → underscore
     rewrite of the original and whose ``inclusion`` is ``INCLUDED``,
   * append it to the ``Files`` collection,
   * remove the original (EXCLUDED) entry so it never reaches the build.
3. Walk every markdown ``File`` (including the rewritten ones) and rewrite
   relative image/link references in its content so they point at the
   underscore path instead of the dot path.

The result is: mkdocs serves ``site/<parent>/_01_xxx_images/foo.png`` while
the source tree still has ``.01_xxx_images/foo.png`` on disk. No source
files are modified.

Register in mkdocs.yml:
    hooks:
        - zz_scripts/docs_hook.py
"""

from __future__ import annotations

import re

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import File, Files, InclusionLevel


_DOT_RE = re.compile(r"\[(?:\"')?([^\[\]]+?)(?:[\"'])?\]\(([^)]+)\)")
_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _fix_path(path: str) -> str:
    """Rewrite a relative path: leading-dot dir components become underscore-prefixed.

    - ``./.01_xxx_images/foo.png`` → ``./_01_xxx_images/foo.png``
    - ``.01_xxx_images/foo.png``   → ``_01_xxx_images/foo.png``
    - ``../../.foo/bar.md``        → ``../../_foo/bar.md``
    """
    if not path:
        return path
    if path.startswith(("http://", "https://", "data:", "mailto:", "//")):
        return path
    # Split into parts preserving leading "./" markers.
    prefix = ""
    rest = path
    while rest.startswith("./"):
        prefix += "./"
        rest = rest[2:]
    parts = rest.split("/")
    new_parts = ["_" + p[1:] if p.startswith(".") else p for p in parts]
    return prefix + "/".join(new_parts)


def _fix_content(text: str) -> str:
    """Rewrite all markdown links/images in a chunk of text."""

    def _link_sub(match: "re.Match[str]") -> str:
        label, target = match.group(1), match.group(2)
        if target.endswith((")", "]")) and " " in target:
            return match.group(0)
        return f"[{label}]({_fix_path(target)})"

    def _img_sub(match: "re.Match[str]") -> str:
        alt, target = match.group(1), match.group(2)
        if target.endswith((")", "]")) and " " in target:
            return match.group(0)
        return f"![{alt}]({_fix_path(target)})"

    text = _IMG_RE.sub(_img_sub, text)
    text = _DOT_RE.sub(_link_sub, text)
    return text


def _has_dot_path(src_uri: str) -> bool:
    """Return True if any path component of ``src_uri`` begins with '.'."""
    if src_uri.startswith("."):
        return True
    return "/." in src_uri


def _make_virtual_file(
    original: File,
    new_src_uri: str,
    config: MkDocsConfig,
    inclusion: InclusionLevel,
) -> File:
    """Create a new in-memory File backed by ``original``'s content.

    The new file uses ``src_dir=None`` (so ``abs_src_path`` is ``None``) and
    stores content via the public setter, which marks it as a virtual file.
    mkdocs' ``copy_file`` then writes ``self._content`` to ``abs_dest_path``.
    """
    new_file = File(
        path=new_src_uri,
        src_dir=None,
        dest_dir=config.site_dir,
        use_directory_urls=config.use_directory_urls,
        inclusion=inclusion,
    )
    # Force inclusion to be a non-cached enum value (set on construction).
    new_file.inclusion = inclusion
    # Read original bytes/text and stash on the virtual file.
    abs_src = original.abs_src_path
    assert abs_src is not None
    if original.is_documentation_page():
        with open(abs_src, encoding="utf-8-sig", errors="strict") as fh:
            text = fh.read()
        new_file.content_string = text
    else:
        with open(abs_src, "rb") as fh:
            data = fh.read()
        new_file.content_bytes = data
    return new_file


def on_files(files: Files, config: MkDocsConfig) -> Files:
    """MkDocs hook: called after the file collection, before page rendering."""
    # Pass 1: rewrite content of every markdown file so image/link references
    # use the underscore path. This must happen first because some markdown
    # files live under dot directories themselves and their references would
    # otherwise be left pointing at the original (excluded) location.
    md_files = 0
    md_modified = 0
    for file_obj in files:
        if not file_obj.is_documentation_page():
            continue
        md_files += 1
        text = file_obj.content_string
        new_text = _fix_content(text)
        if new_text != text:
            file_obj.content_string = new_text
            md_modified += 1

    # Pass 2: for every file inside a dot directory (these are present in the
    # collection but flagged EXCLUDED by mkdocs' ``.*`` default), create a
    # sibling in-memory File with the underscore path and INCLUDED status.
    dot_files = [f for f in files if _has_dot_path(f.src_uri)]
    rewritten = 0
    for original in dot_files:
        new_src_uri = _fix_path(original.src_uri)
        if new_src_uri == original.src_uri:
            continue
        virtual = _make_virtual_file(
            original,
            new_src_uri,
            config,
            InclusionLevel.INCLUDED,
        )
        # If the rewritten path is a markdown file, also patch its content.
        if virtual.is_documentation_page():
            text = virtual.content_string
            virtual.content_string = _fix_content(text)
        files.append(virtual)
        files.remove(original)
        rewritten += 1

    if md_modified or rewritten:
        print(
            f"[docs_hook] md_files={md_files}, md_modified={md_modified}, "
            f"dot_files_rewritten={rewritten}, total_files={len(files)}"
        )
    return files