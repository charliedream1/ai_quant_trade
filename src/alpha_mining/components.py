"""Approved research versions adapt to the existing graph and risk/portfolio execution."""

from datetime import timedelta

import numpy as np

from src.strategy.composition.contracts import Frame, Observation

from .approvals import require_approved
from .config import digest, invalid
from .contracts import ResearchPermit
from .factors import evaluate_expression, market_panel
from .pit import timestamp
from .store import AlphaStore


class AlphaRuntime:
    def __init__(self, permit: ResearchPermit | None = None):
        self.permit = permit
        self.cache: dict[tuple, tuple[dict, dict | None]] = {}

    def evaluate(self, node: dict, symbols: list[str], frame: Frame) -> dict[str, Observation]:
        params = node["params"]
        study_id, candidate_id = params["study_id"], params.get("candidate_id", params.get("configuration", 0))
        if isinstance(self.permit, ResearchPermit) and (self.permit.study_id, self.permit.candidate_id) == (
            study_id,
            candidate_id,
        ):
            return self._scores(self.permit.scores, symbols, frame.as_of, self.permit.targets)
        key = (study_id, candidate_id, params.get("artifact_digest", ""))
        if key not in self.cache:
            store = AlphaStore()
            study = store.get("alpha_studies", study_id)
            candidate = store.get("alpha_candidates", candidate_id) if node["component"] == "alpha_factor" else None
            if candidate and candidate["study_id"] != study_id:
                raise invalid("因子不属于所选研究")
            require_approved(store, study, candidate)
            expected = candidate["digest"] if candidate else digest(study["result"])
            if params["artifact_digest"] != expected:
                raise invalid("研究产物摘要已变化，请重新导出工坊草稿")
            self.cache[key] = study, candidate
        study, candidate = self.cache[key]
        if candidate:
            panel = market_panel(frame.mutable_history())
            values = (
                evaluate_expression(candidate["implementation"]["expression"], panel)
                * candidate["hypothesis"]["direction"]
            )
            return self._scores(values, symbols, frame.as_of)
        if node["component"] == "alpha_theme":
            if frame.as_of < study["config"]["cutoff"][:10]:
                raise invalid("不能在主题信息可得日期之前使用该冻结主题池")
            names = set(study["result"]["frozen_symbols"])
            return {
                symbol: Observation(
                    symbol,
                    1.0 if symbol in names else None,
                    "pass" if symbol in names else "reject",
                    "theme_evidence",
                    evidence={"study_id": study_id},
                )
                for symbol in symbols
            }
        eligible = [
            row
            for row in study["result"].get("decisions", [])
            if row["cutoff"][:10] <= frame.as_of and row.get("configuration") == params["configuration"]
        ]
        latest = max(eligible, key=lambda row: row["cutoff"]) if eligible else {}
        if latest and timestamp(latest["cutoff"]) + timedelta(
            days=study["config"]["regime"]["validity_days"]
        ) < timestamp(frame.as_of + "T00:00:00+00:00"):
            latest = {}
        weights = latest.get("weights") or {}
        return {
            symbol: Observation(
                symbol,
                weights.get(symbol, 0.0),
                "pass" if weights.get(symbol, 0) > 0 else "reject",
                "frozen_regime_allocation",
                evidence={"study_id": study_id},
                semantics="target_weight",
            )
            for symbol in symbols
        }

    @staticmethod
    def _scores(values, symbols, day, targets=False):
        row = values.loc[day] if day in values.index else {}
        return {
            symbol: Observation(
                symbol,
                float(row[symbol]) if symbol in row and np.isfinite(row[symbol]) else None,
                "pass" if symbol in row and np.isfinite(row[symbol]) else "unknown",
                "alpha_research",
                semantics="target_weight" if targets else "relative_strength",
                family="alpha",
            )
            for symbol in symbols
        }
