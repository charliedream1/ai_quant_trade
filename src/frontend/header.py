"""Header HTML constants for the Gradio workbench."""

from __future__ import annotations

GITHUB_URL = "https://github.com/charliedream1/ai_quant_trade"
GITEE_URL = "https://gitee.com/charlie1/ai_quant_trade.git"
ZSXQ_URL = "https://t.zsxq.com/dHt9l"

_GITHUB_ICON = (
    "<svg viewBox='0 0 16 16' width='15' height='15' aria-hidden='true'>"
    "<path fill='currentColor' d='M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 "
    "0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 "
    "1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 "
    "0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.42 7.42 0 0 1 2-.27c.68 0 1.36.09 "
    "2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 "
    "3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z'/>"
    "</svg>"
)
_GITEE_ICON = (
    "<svg viewBox='0 0 24 24' width='15' height='15' aria-hidden='true'>"
    "<path fill='currentColor' d='M11.984 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.016 0Zm6.34 5.33c.29 0 .53.1.7.31.17.2.23.48.17.82l-1.26 5.62"
    "c-.08.36-.15.66-.2.9-.06.24-.18.45-.37.62-.19.18-.42.32-.7.42-.28.11-.61.16-.99.16H8.21l.95-1.7h6.06l1-4.47"
    "H7.12l.43-1.72h10.08l.43-1.93H6.36L5.43 7.3c-.13-.54-.03-.97.28-1.28.31-.3.77-.46 1.36-.46h11.25ZM7.3 14.96l"
    "-2.05 3.53c-.14.24-.33.42-.57.53-.24.11-.5.15-.77.1-.28-.05-.5-.19-.66-.42-.17-.23-.23-.5-.19-.81l.6-2.93H7.3Z'/>"
    "</svg>"
)
_ZSXQ_ICON = (
    "<svg viewBox='0 0 24 24' width='15' height='15' aria-hidden='true'>"
    "<path fill='currentColor' d='M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 4.2c1.2 0 2.17.97 2.17 2.17A2.17 2.17 0 1 1 12 6.2Zm-3.1 5.15h6.2a.78.78 0 0 1 .78.78v.55"
    "c0 1.9-1.3 3.52-3.1 3.97v1.58h-1.55v-1.58a4.14 4.14 0 0 1-3.1-3.97v-.55c0-.43.34-.78.77-.78Zm1.02 1.4v.05"
    "c0 1.05.7 1.94 1.66 2.22l.42.12.42-.12a2.35 2.35 0 0 0 1.66-2.22v-.05H9.92Z'/>"
    "</svg>"
)
_REFRESH_ICON = (
    "<svg viewBox='0 0 24 24' width='16' height='16' aria-hidden='true'>"
    "<path fill='none' stroke='currentColor' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round' "
    "d='M20 11A8 8 0 0 0 6.3 6.3L4 8.5M4 4v4.5h4.5M4 13a8 8 0 0 0 13.7 4.7l2.3-2.2M20 20v-4.5h-4.5'/>"
    "</svg>"
)
_LANGUAGE_ICON = (
    "<svg viewBox='0 0 24 24' width='15' height='15' aria-hidden='true'>"
    "<path fill='none' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round' "
    "d='M3 5h9M7.5 3.5v1.5c0 4.5-2 8.5-4.5 10.5M5 9c1.5 3 4 5.5 7 6.5M13 20.5l4-11 4 11M14.8 17h4.4'/>"
    "</svg>"
)


def _external_link(href: str, label: str, icon: str) -> str:
    return (
        f"<a class='app-header-link' href='{href}' target='_blank' rel='noopener noreferrer' title='{label}'>"
        f"{icon}<span>{label}</span></a>"
    )


def external_links_html() -> str:
    """Share the original project/community destinations with every header."""
    return "".join(
        [
            _external_link(GITHUB_URL, "GitHub", _GITHUB_ICON),
            _external_link(GITEE_URL, "Gitee", _GITEE_ICON),
            _external_link(ZSXQ_URL, "知识星球", _ZSXQ_ICON),
        ]
    )


def header_html() -> str:
    """Compact tech-style top bar with logo, title, market/language toggles and links."""
    links = external_links_html()
    return (
        "<div class='app-header'><div class='app-header-grid'>"
        "<div class='app-header-brand'>"
        "<img class='app-header-logo' src='/static/logo.png' alt='AIQuant智投 Logo'/>"
        "<div class='app-header-titles'><h1>AIQuant智投</h1>"
        "<p>一体化量化研究与交易工作台</p></div></div>"
        "<div class='app-header-actions'>"
        f"<div class='app-header-links'>{links}</div>"
        "<div class='app-header-toggle-group'>"
        "<button id='app-language-toggle' type='button' class='app-header-toggle' "
        "title='切换中英文界面 / Toggle UI language'>"
        f"{_LANGUAGE_ICON}<span id='app-language-label'>中 / EN</span></button>"
        "<div class='app-market-toggle' role='group' aria-label='市场切换'>"
        "<button type='button' id='app-market-cn' class='app-market-option active' title='切换到 A 股市场'>A股</button>"
        "<button type='button' id='app-market-us' class='app-market-option' title='切换到美股市场'>美股</button>"
        "</div>"
        "</div>"
        f"<button id='app-refresh-button' type='button' title='刷新当前页面'>{_REFRESH_ICON}"
        "<span>刷新</span></button>"
        "</div></div></div>"
    )
