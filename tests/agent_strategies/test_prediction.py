"""Statistical formulas and real local LightGBM fitting, not prerecorded model outputs."""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.agent_strategies.config import freeze
from src.agent_strategies.contest import select_information
from src.agent_strategies.predict import predict

FIXTURE = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("workflows.yaml").read_text(encoding="utf-8"))


def samples():
    cfg = FIXTURE["predict"]
    return [
        {
            "value": cfg["offset"] + cfg["amplitude"] * np.sin(index / cfg["cycle"]),
            "effective_at": (date(2020, 1, 1) + timedelta(days=index)).isoformat() + "T00:00:00+00:00",
        }
        for index in range(cfg["points"])
    ]


def test_statistical_baseline_matches_independent_reference():
    cfg = freeze("contest_event")
    rows = samples()
    result = predict(rows, cfg)
    values = np.asarray([row["value"] for row in rows[-cfg["policy"]["score_window"] :]])
    weights = np.power(1 - cfg["policy"]["ewma_alpha"], np.arange(len(values) - 1, -1, -1))
    expected = np.sum(weights * values) / weights.sum() * (1 - cfg["policy"]["shrinkage"]) / values.std(ddof=1)
    assert result["utility"] == pytest.approx(expected)
    assert result["fitted"] is False and result["method"] == "baseline"
    assert predict(rows[:2], cfg)["status"] == "cold"


def test_lightgbm_is_fitted_and_saves_native_models(tmp_path):
    pytest.importorskip("lightgbm")
    cfg = freeze("contest_event", {"predictor": "lightgbm", "score_window": 180})
    result = predict(samples(), cfg, tmp_path / "utility.txt")
    assert result["fitted"] and result["training_samples"] >= cfg["policy"]["min_training"]
    assert result["training_cutoff"] == samples()[-1]["effective_at"]
    assert len(result["artifacts"]) == 2 and (tmp_path / result["artifacts"][0]["file"]).is_file()
    assert predict(samples()[:15], cfg)["status"] == "insufficient_training"


def test_data_contest_excludes_negative_utility_and_budget_excess():
    cfg = freeze("contest_event")
    observed = [
        {"id": "a", "actor": "positive", "text": "独立事件甲", "quote": "原文甲", "source_id": "d1", "symbol": "AAA"},
        {"id": "b", "actor": "negative", "text": "另一事件乙", "quote": "原文乙", "source_id": "d2", "symbol": "BBB"},
    ]
    forecasts = {
        "positive": {"status": "estimated", "utility": 1.0},
        "negative": {"status": "estimated", "utility": -1.0},
    }
    result = select_information(observed, forecasts, cfg)
    assert [row["id"] for row in result["selected"]] == ["a"]
    assert result["dropped"][0]["reason"] == "non_positive_or_unavailable_utility"
    cfg["limits"]["context_chars"] = 1
    assert not select_information(observed, forecasts, cfg)["selected"]
