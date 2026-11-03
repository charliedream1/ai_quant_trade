"""Modular Gradio feature renderers."""

from .admin import render_admin
from .ai import render_ai
from .assistant import render_floating_assistant
from .dashboard import render_dashboard
from .knowledge import render_knowledge
from .live import render_live
from .market import render_market
from .research import render_research
from .simulation import render_simulation
from .strategy import render_strategy

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
