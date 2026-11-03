"""Shared actual model backends, fitted on a full historical mother universe."""

from hashlib import sha256
from importlib import import_module
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from src.strategy.composition.config import fail
from src.strategy.composition.contracts import Frame, Observation
from src.strategy.composition.model_artifacts import ModelArtifacts
from src.strategy.composition.validation import digest
from src.strategy.factors.cache import FactorCache
from src.strategy.factors.config import factor_set
from src.strategy.factors.panel import PanelBuilder
from src.strategy.models.config import BACKEND_MODULES
from src.strategy.models.features import build_panel, time_split


class ScoreModel:
    def __init__(
        self,
        component: str,
        params: dict[str, Any],
        artifacts: ModelArtifacts | None = None,
        factor_contract: dict[str, Any] | None = None,
    ):
        self.component, self.params = component, params
        self.model: Any = None
        self.artifacts = artifacts
        self.feature_builder: PanelBuilder | None = None
        self.factor_contract = factor_contract or {}
        self.last_fit = ""
        self.cycles = 0
        self.fit_cycle = 0
        self.diagnostics: dict[str, Any] = {"fits": [], "predictions": 0, "status": "warming_up"}

    def predict(self, symbols: list[str], frame: Frame, emit) -> dict[str, Observation]:
        if self.params["demean_target"] and len(frame.history) < 2:
            raise fail("model_failed", "relative target requires multiple mother-universe assets")
        self.cycles = int(frame.account.get("session", self.cycles + 1))
        if self.params.get("feature_set") and self.feature_builder is None:
            self.feature_builder = PanelBuilder(FactorCache() if self.artifacts else None, self.factor_contract)
        panel = build_panel(frame.mutable_history(), self.params, self.feature_builder)
        matured = [row for row in panel if row.target_date and row.target_date <= frame.as_of]
        train, validation = time_split(matured, self.params)
        if not train:
            return {symbol: Observation(symbol, None, "unknown", "model_warming") for symbol in symbols}
        if self.model is None or self.cycles - self.fit_cycle >= self.params["retrain_interval"]:
            start = perf_counter()
            key = digest(
                {
                    "component": self.component,
                    "params": self.params,
                    "environment": {
                        key: version(key)
                        for key in (
                            "numpy",
                            "scikit-learn",
                            "torch" if self.params["backend"] == "mlp" else self.params["backend"],
                        )
                    },
                    "as_of": frame.as_of,
                    "training": [[r.symbol, r.date, r.target_date, r.values, r.target] for r in train],
                    "source": sha256(
                        Path(__file__).read_bytes()
                        + Path(str(import_module(BACKEND_MODULES[self.params["backend"]]).__file__)).read_bytes()
                    ).hexdigest(),
                }
            )
            cached = self.artifacts.metadata(key) if self.artifacts else None
            kind = "model_cache" if cached else "model_fit"
            emit(kind, self.component, {"status": "started", "as_of": frame.as_of, "train_samples": len(train)})
            try:
                backend = import_module(BACKEND_MODULES[self.params["backend"]])
                if cached and self.artifacts:
                    model = self.artifacts.load(cached)
                else:
                    model = backend.build_model(self.params["model_params"])
                    model.fit(
                        np.asarray([row.values for row in train]),
                        np.asarray([row.target for row in train], dtype=float),
                    )
                predicted = np.asarray(model.predict(np.asarray([row.values for row in validation])))
                if predicted.shape != (len(validation),) or not np.isfinite(predicted).all():
                    raise fail("model_failed")
            except ImportError as exc:
                raise fail("unavailable", self.component) from exc
            self.model = model
            self.last_fit = frame.as_of
            self.fit_cycle = self.cycles
            fit = {
                "feature_set": self.params.get("feature_set") or "legacy_price_volume",
                "feature_names": list(self.factor_contract.get("definitions") or factor_set(self.params["feature_set"]))
                if self.params.get("feature_set")
                else [],
                "factor_contract": self.factor_contract,
                "as_of": frame.as_of,
                "train_start": min(r.date for r in train),
                "train_end": max(r.date for r in train),
                "label_end": max(r.target_date for r in train),
                "validation_start": min(r.date for r in validation),
                "validation_label_end": max(r.target_date for r in validation),
                "train_samples": len(train),
                "validation_samples": len(validation),
                "validation_mse": float(
                    np.mean((predicted - np.asarray([r.target for r in validation], dtype=float)) ** 2)
                ),
                "duration_ms": round((perf_counter() - start) * 1000, 2),
                "actual_fit": not bool(cached),
            }
            if self.artifacts:
                artifact = cached or self.artifacts.save(
                    key, model, self.params["backend"], self.params["model_params"], dict(fit)
                )
                fit["artifact"] = {k: artifact[k] for k in ("id", "file", "format", "sha256", "created_at")}
            self.diagnostics["fits"].append(fit)
            self.diagnostics["status"] = "fitted"
            emit(kind, self.component, {"status": "completed", **fit})
        current = {row.symbol: row for row in panel if row.date == frame.as_of and row.symbol in symbols}
        if not current:
            return {}
        ordered = sorted(current)
        values = np.asarray(self.model.predict(np.asarray([current[s].values for s in ordered])))
        if values.shape != (len(ordered),) or not np.isfinite(values).all():
            raise fail("model_failed")
        self.diagnostics["predictions"] += len(ordered)
        return {
            s: Observation(
                s,
                float(value),
                evidence={"model": self.component, "fit_as_of": self.last_fit},
                horizon=self.params["horizon"],
                semantics="relative_return" if self.params["demean_target"] else "absolute_return",
                family=self.component,
            )
            for s, value in zip(ordered, values, strict=True)
        }
