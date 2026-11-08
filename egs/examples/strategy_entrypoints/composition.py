"""Registry entrypoint; actual target execution requires the composition engine."""

from src.strategy.strategy_base import StrategyBase


class CompositePipelineStrategy(StrategyBase):
    name = "CompositePipelineStrategy"
    version = "v1"
    params_schema = [
        {"name": "pipeline_id", "type": "int", "required": True},
        {"name": "pipeline_version", "type": "int", "required": True},
    ]

    def on_start(self, context):
        context["metadata"]["requires_composition"] = True

    def on_bar(self, bar):
        return []
