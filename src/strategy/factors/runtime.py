"""Typed factor stages adapted to the existing candidate/event runtime."""

from typing import Any

from src.strategy.composition.contracts import Frame, Observation

from .cache import FactorCache
from .panel import FactorPanel, PanelBuilder, preprocess
from .research import select
from .scoring import score


class FactorRuntime:
    def __init__(self, persistent: bool = False):
        self.persistent = persistent
        self.cache: FactorCache | None = None
        self.builders: dict[str, PanelBuilder] = {}
        self.panels: dict[str, FactorPanel] = {}
        self.diagnostics: dict[str, dict[str, Any]] = {}

    def evaluate(self, node: dict[str, Any], symbols: list[str], frame: Frame) -> dict[str, Observation]:
        component, params, key = node["component"], node["params"], node["id"]
        if component == "factor_set":
            if self.persistent and self.cache is None:
                self.cache = FactorCache()
            builder = self.builders.setdefault(key, PanelBuilder(self.cache, node.get("factor_contract")))
            panel = builder.build(dict(frame.history), params["set_name"])
        else:
            parent = self.panels[node["inputs"][0]]
            if component == "factor_preprocess":
                panel = preprocess(parent, params)
            elif component == "factor_select":
                panel = select(parent, dict(frame.history), frame.as_of, params)
            else:
                result = score(parent, symbols, frame.as_of, params)
                self.diagnostics[key] = {
                    "as_of": frame.as_of,
                    "weighting": params["weighting"],
                    "observations": {s: row.evidence for s, row in result.items()},
                }
                return result
        self.panels[key] = panel
        self.diagnostics[key] = {"as_of": frame.as_of, **panel.metadata, "factors": list(panel.values.columns)}
        current = panel.values.loc[frame.as_of] if frame.as_of in panel.values.index.get_level_values("date") else None
        output = {}
        for symbol in symbols:
            factors = current.loc[symbol].dropna().to_dict() if current is not None and symbol in current.index else {}
            output[symbol] = Observation(
                symbol,
                None,
                evidence={
                    "factor_set": panel.metadata["set"],
                    "factors": factors,
                    "selected": list(panel.values.columns),
                    "definition_digest": panel.metadata["definition_digest"],
                },
                family="factor",
            )
        return output
