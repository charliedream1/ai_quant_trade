"""Let Material's native language selector resolve pages through language sitemaps."""

import re
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from mkdocs.plugins import event_priority
from mkdocs.utils import get_relative_url


@event_priority(-100)
def on_page_context(context, page, config, nav):
    """Restore language roots after i18n supplies per-page alternate URLs.

    Material 9.8 loads a sitemap from each alternate. Giving it a deep-page URL
    causes spurious sitemap 404s; the native selector already preserves pages.
    """
    languages = context.get("i18n_config", {}).get("languages", [])
    language = next((item for item in languages if item["locale"] == context.get("i18n_page_locale")), None)
    if not language or not languages:
        return context
    root = urlsplit(config.site_url or "/").path
    if not language["default"]:
        root = root.removesuffix(language["link"])
    root = root.rstrip("/") + "/"
    alternates = [
        {
            "name": item["name"],
            "lang": item["locale"],
            "link": item["fixed_link"] or root + item["link"].lstrip("/"),
        }
        for item in languages
        if item["build"]
    ]
    # i18n sets a LegacyConfig attribute; Jinja prefers it over the mapping key.
    config.extra.alternate = alternates
    config.extra["alternate"] = alternates
    return context


@event_priority(-200)
def on_post_page(output, page, config):
    """Use i18n's explicit page links without Material's root-link interception."""
    alternates = getattr(page.file, "alternates", {})

    def page_link(match):
        tag = match.group(0)
        if not re.search(r'class="[^"]*\bmd-select__link\b', tag):
            return tag
        language = re.search(r'hreflang="([^"]+)"', tag)
        alternate = alternates.get(language.group(1)) if language else None
        if alternate is None:
            return tag
        href = escape(get_relative_url(alternate.url, page.url), quote=True)
        tag = re.sub(r'href="[^"]*"', lambda _: f'href="{href}"', tag, count=1)
        # _self is still the same tab; it also opts out of native root fallback.
        return tag[:-1] + ' target="_self">'

    return re.sub(r"<a\b[^>]*>", page_link, output)


@event_priority(-200)
def on_post_build(config):
    """Expose the combined i18n sitemap at each built language's root."""
    plugin = config.plugins.get("i18n")
    if plugin is None:
        return
    site = Path(config.site_dir).resolve()
    source = site / "sitemap.xml"
    if not source.is_file():
        return
    for language in plugin.config.languages:
        if not language["build"]:
            continue
        target = (site / language["link"].strip("/") / "sitemap.xml").resolve()
        if target == source:
            continue
        if not target.is_relative_to(site):
            raise ValueError("Language sitemap must stay inside site_dir")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
