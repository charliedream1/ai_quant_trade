"""Cross-application navigation for the modular Gradio frontend."""

from __future__ import annotations

from html import escape

from .registry import MODULES


def module_navigation_html(active_key: str) -> str:
    links = []
    for module in MODULES:
        active = module.key == active_key
        classes = "module-nav-link active" if active else "module-nav-link"
        current = " aria-current='page'" if active else ""
        links.append(
            f"<a class='{classes}' data-module-key='{escape(module.key)}' "
            f"href='../{escape(module.slug)}/'{current}>{escape(module.title)}</a>"
        )
    return (
        f"<nav id='module-navigation' data-gradio-module-nav data-gradio-module='{escape(active_key)}' "
        "aria-label='主功能导航'>" + "".join(links) + "</nav>"
    )
