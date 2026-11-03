"""Market research callback boundary."""

from .base import DomainHandler


class MarketHandler(DomainHandler):
    domain = "market"
    allowed_methods = frozenset(
        {
            "economic_models",
            "economic_load",
            "economic_report",
            "economic_open",
            "add_recommendations_to_resource_pool",
            "add_recommendations_to_watchlist",
            "add_resource_pool_symbols",
            "add_stock_to_watchlist",
            "add_watchlist_symbols",
            "create_resource_pool",
            "create_watchlist_group",
            "export_relations",
            "market_overview",
            "news",
            "news_detail",
            "pipeline_pool_run",
            "pipeline_templates",
            "recommend",
            "recommend_candidate_compare",
            "recommend_condition_template",
            "recommend_first_to_relations",
            "recommend_group_compare",
            "recommend_load_template",
            "recommend_save_template",
            "recommend_templates",
            "recommend_to_backtest",
            "refresh_news",
            "relation_evidence_detail",
            "relation_evidence_options",
            "relation_fit",
            "relations",
            "remove_watchlist_symbol",
            "resource_import_commit",
            "resource_import_preview",
            "resource_pool_items",
            "resource_pool_to_universe",
            "resource_pools",
            "resource_template",
            "security_master_search",
            "stock",
            "stock_to_relations",
            "watchlist_groups",
        }
    )
