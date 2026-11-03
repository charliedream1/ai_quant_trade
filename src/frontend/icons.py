"""Small local SVG icons shared by workspace navigation."""

from html import escape

_MODULE_PATHS = {
    "dashboard": "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
    "market": "M3 19h18 M4 15l5-6 4 3 7-9 M16 3h4v4",
    "research": "M5 3h10l4 4v14H5z M14 3v5h5 M8 12h8 M8 16h6",
    "strategy": "M4 4h6v6H4z M14 14h6v6h-6z M14 4h6v6h-6z M7 10v7h7 M10 7h4",
    "simulation": "M4 7h15l-4-4 M20 17H5l4 4 M19 7l-4 4 M5 17l4-4",
    "live": "M12 3v9 M7 5a9 9 0 1 0 10 0",
    "ai": "M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z",
    "knowledge": "M3 4h6l3 2 3-2h6v15h-6l-3 2-3-2H3z M12 6v15 M6 8h3 M15 8h3",
    "learning": "M2 9l10-6 10 6-10 6z M6 12v6l6 3 6-3v-6 M22 9v8",
    "admin": "M5 3v18 M12 3v18 M19 3v18 M2 8h6 M9 15h6 M16 8h6",
}


def module_icon(module_key: str) -> str:
    """Return a crisp icon without external fonts or network requests."""
    path = escape(_MODULE_PATHS.get(module_key, _MODULE_PATHS["dashboard"]), quote=True)
    return (
        "<svg viewBox='0 0 24 24' aria-hidden='true' width='22' height='22'>"
        f"<path d='{path}' fill='none' stroke='currentColor' stroke-width='1.8' "
        "stroke-linecap='round' stroke-linejoin='round'/></svg>"
    )
