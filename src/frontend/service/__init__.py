"""Compatible domain exports loaded only when requested."""

from importlib import import_module

EXPORTS = {
    "annotations": ("__future__", "annotations"),
    "AdminServiceMixin": (".admin", "AdminServiceMixin"),
    "AIServiceMixin": (".ai", "AIServiceMixin"),
    "AssistantServiceMixin": (".assistant", "AssistantServiceMixin"),
    "DashboardServiceMixin": (".dashboard", "DashboardServiceMixin"),
    "ETFServiceMixin": (".etf", "ETFServiceMixin"),
    "KnowledgeServiceMixin": (".knowledge", "KnowledgeServiceMixin"),
    "LiveServiceMixin": (".live", "LiveServiceMixin"),
    "MarketServiceMixin": (".market", "MarketServiceMixin"),
    "ParameterServiceMixin": (".parameters", "ParameterServiceMixin"),
    "ResearchServiceMixin": (".research", "ResearchServiceMixin"),
    "SimulationServiceMixin": (".simulation", "SimulationServiceMixin"),
    "StrategyServiceMixin": (".strategy", "StrategyServiceMixin"),
}

__all__ = [
    "DashboardServiceMixin",
    "MarketServiceMixin",
    "ResearchServiceMixin",
    "StrategyServiceMixin",
    "SimulationServiceMixin",
    "ParameterServiceMixin",
    "ETFServiceMixin",
    "LiveServiceMixin",
    "KnowledgeServiceMixin",
    "AIServiceMixin",
    "AdminServiceMixin",
    "AssistantServiceMixin",
]


def __getattr__(name):
    if name not in EXPORTS:
        raise AttributeError(name)
    module, symbol = EXPORTS[name]
    value = getattr(import_module(module, __name__), symbol)
    globals()[name] = value
    return value
