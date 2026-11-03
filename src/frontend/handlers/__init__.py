"""Domain-scoped callback handlers for modular Gradio pages."""

from __future__ import annotations

from dataclasses import dataclass

from ..service_dispatch import CallbackService
from .admin import AdminHandler
from .ai import AIHandler
from .assistant import AssistantHandler
from .base import DomainHandler
from .dashboard import DashboardHandler
from .knowledge import KnowledgeHandler
from .live import LiveHandler
from .market import MarketHandler
from .research import ResearchHandler
from .simulation import SimulationHandler
from .strategy import StrategyHandler


@dataclass(frozen=True, slots=True)
class FrontendHandlers:
    dashboard: DashboardHandler
    market: MarketHandler
    research: ResearchHandler
    strategy: StrategyHandler
    simulation: SimulationHandler
    live: LiveHandler
    ai: AIHandler
    knowledge: KnowledgeHandler
    admin: AdminHandler
    assistant: AssistantHandler


def build_frontend_handlers(service: CallbackService) -> FrontendHandlers:
    return FrontendHandlers(
        dashboard=DashboardHandler(service),
        market=MarketHandler(service),
        research=ResearchHandler(service),
        strategy=StrategyHandler(service),
        simulation=SimulationHandler(service),
        live=LiveHandler(service),
        ai=AIHandler(service),
        knowledge=KnowledgeHandler(service),
        admin=AdminHandler(service),
        assistant=AssistantHandler(service),
    )


__all__ = ["DomainHandler", "FrontendHandlers", "build_frontend_handlers"]
