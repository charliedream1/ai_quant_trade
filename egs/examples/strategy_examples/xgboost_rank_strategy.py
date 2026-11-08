"""XGBoost cross-sectional factor ranking with next-session execution."""

from src.strategy.models.runtime import ModelStrategy


class XGBoostRankStrategy:
    def __init__(self, params=None):
        self.runtime = ModelStrategy("xgboost_rank", params)

    def on_start(self, context):
        self.runtime.on_start(context)

    def handle_bar(self, bar, context):
        return self.runtime.on_bar(bar, context)

    def on_stop(self, context):
        self.runtime.on_stop(context)
