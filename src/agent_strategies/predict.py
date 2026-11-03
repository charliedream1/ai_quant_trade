"""Explicit statistical baseline and locally fitted, time-bounded LightGBM utility."""

from hashlib import sha256
from importlib import import_module

import numpy as np


def features(values: list[float], windows: list[int]) -> list[float]:
    return [
        number for window in windows for number in (float(np.mean(values[-window:])), float(np.std(values[-window:])))
    ]


def predict(rows: list[dict], cfg: dict, path=None) -> dict:
    p = cfg["policy"]
    rows = rows[-p["score_window"] :]
    values = [row["value"] for row in rows]
    result = {
        "method": p["predictor"],
        "samples": len(values),
        "utility": None,
        "status": "cold",
        "latest_label": rows[-1]["effective_at"] if rows else None,
    }
    if len(values) < p["min_history"]:
        return result
    if p["predictor"] == "baseline":
        weights = (1 - p["ewma_alpha"]) ** np.arange(len(values) - 1, -1, -1)
        mean = float(np.average(values, weights=weights)) * (1 - p["shrinkage"])
        std = float(np.std(values, ddof=1))
        if std <= p["volatility_floor"]:
            return {**result, "status": "degenerate"}
        return {**result, "utility": mean / std, "mean": mean, "std": std, "status": "estimated", "fitted": False}
    windows, horizon = p["feature_windows"], p["prediction_horizon"]
    training, means, deviations = [], [], []
    for index in range(max(windows), len(values) - horizon + 1):
        future = values[index : index + horizon]
        training.append(features(values[:index], windows))
        means.append(float(np.mean(future)))
        deviations.append(max(float(np.std(future, ddof=1)), p["volatility_floor"]))
    if len(training) < p["min_training"]:
        return {**result, "status": "insufficient_training", "training_samples": len(training)}
    lgb = import_module("lightgbm")
    models, predicted, hashes = [], [], []
    for label, targets in (("mean", means), ("std", deviations)):
        model = lgb.LGBMRegressor(**p["model_params"], random_state=p["seed"])
        model.fit(np.asarray(training), np.asarray(targets))
        predicted.append(float(model.booster_.predict(np.asarray([features(values, windows)]))[0]))
        if path is not None:
            target = path.with_name(path.stem + "-" + label + ".txt")
            target.parent.mkdir(parents=True, exist_ok=True)
            model.booster_.save_model(str(target))
            hashes.append({"file": target.name, "sha256": sha256(target.read_bytes()).hexdigest()})
        models.append(model)
    return {
        **result,
        "status": "estimated",
        "fitted": True,
        "training_samples": len(training),
        "training_cutoff": rows[-1]["effective_at"],
        "mean": predicted[0],
        "std": max(predicted[1], p["volatility_floor"]),
        "utility": predicted[0] / max(predicted[1], p["volatility_floor"]),
        "artifacts": hashes,
    }
