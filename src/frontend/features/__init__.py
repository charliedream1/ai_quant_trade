"""Compatible domain exports loaded only when requested."""

from importlib import import_module

EXPORTS = {
    "render_admin": (".admin", "render_admin"),
    "render_ai": (".ai", "render_ai"),
    "render_floating_assistant": (".assistant", "render_floating_assistant"),
    "render_dashboard": (".dashboard", "render_dashboard"),
    "render_knowledge": (".knowledge", "render_knowledge"),
    "render_live": (".live", "render_live"),
    "render_market": (".market", "render_market"),
    "render_research": (".research", "render_research"),
    "render_simulation": (".simulation", "render_simulation"),
    "render_strategy": (".strategy", "render_strategy"),
}

__all__ = [
    "render_admin",
    "render_ai",
    "render_dashboard",
    "render_floating_assistant",
    "render_knowledge",
    "render_live",
    "render_market",
    "render_research",
    "render_simulation",
    "render_strategy",
]


def __getattr__(name):
    if name not in EXPORTS:
        raise AttributeError(name)
    module, symbol = EXPORTS[name]
    value = getattr(import_module(module, __name__), symbol)
    globals()[name] = value
    return value
