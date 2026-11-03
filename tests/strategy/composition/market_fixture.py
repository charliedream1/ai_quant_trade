"""Seeded offline price fixture; never presented as live market evidence."""

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

CONFIG = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("market.yaml").read_text(encoding="utf-8"))


def snapshot():
    dates = pd.bdate_range(CONFIG["start"], periods=CONFIG["sessions"]).strftime("%Y-%m-%d").tolist()
    random = np.random.default_rng(CONFIG["seed"])
    history = {}
    for symbol, p in CONFIG["symbols"].items():
        price = p["price"]
        rows = []
        for day in dates:
            opening = price * (1 + random.normal(0, CONFIG["overnight_volatility"]))
            close = opening * (1 + random.normal(p["drift"], p["volatility"]))
            rows.append(
                {
                    "date": day,
                    "timestamp": day,
                    "open": opening,
                    "close": close,
                    "high": max(opening, close) * (1 + CONFIG["spread"]),
                    "low": min(opening, close) * (1 - CONFIG["spread"]),
                    "volume": CONFIG["volume"],
                    "amount": close * CONFIG["volume"],
                }
            )
            price = close
        history[symbol] = rows
    metadata = {
        s: {
            "sector": p["sector"],
            "asset_class": "etf" if s in {"510300", "510500", "159915", "512100"} else "stock",
            "tradable": True,
            "available_at": dates[0],
            "source": "synthetic_fixture",
        }
        for s, p in CONFIG["symbols"].items()
    }
    return {
        "history": history,
        "metadata": metadata,
        "source": "synthetic_fixture",
        "is_mock": True,
        "market": "CN",
        "limitations": ["synthetic_fixture"],
    }


def small_models(plan):
    for node in plan["nodes"]:
        if node["component"] in CONFIG["model_overrides"]["model_params"]:
            node["params"].update({k: v for k, v in CONFIG["model_overrides"].items() if k != "model_params"})
            node["params"]["model_params"].update(CONFIG["model_overrides"]["model_params"][node["component"]])
    for child in plan["sleeves"]:
        small_models(child["definition"])
    return plan
