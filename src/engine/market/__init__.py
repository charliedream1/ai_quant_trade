"""Compatible domain exports loaded only when requested."""

from importlib import import_module

EXPORTS = {
    "NewsAggregator": (".news_aggregator", "NewsAggregator"),
    "PaperSearchService": (".paper_search", "PaperSearchService"),
    "QuoteService": (".quote_service", "QuoteService"),
    "Recommender": (".recommender", "Recommender"),
    "RelationGraphService": (".relation_graph", "RelationGraphService"),
    "MarketReportGenerator": (".report_generator", "MarketReportGenerator"),
    "ResourcePoolService": (".resource_pool", "ResourcePoolService"),
    "StockAnalyzer": (".stock_analyzer", "StockAnalyzer"),
}

__all__ = [
    "MarketReportGenerator",
    "NewsAggregator",
    "PaperSearchService",
    "QuoteService",
    "Recommender",
    "RelationGraphService",
    "ResourcePoolService",
    "StockAnalyzer",
]


def __getattr__(name):
    if name not in EXPORTS:
        raise AttributeError(name)
    module, symbol = EXPORTS[name]
    value = getattr(import_module(module, __name__), symbol)
    globals()[name] = value
    return value
