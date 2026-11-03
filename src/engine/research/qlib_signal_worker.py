"""Isolated Qlib signal analysis protocol; no provider or model training required."""

from __future__ import annotations

import contextlib
import json
import sys
from importlib.metadata import version
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from qlib.contrib.eva.alpha import calc_ic


def analyze_signals(payload: dict[str, Any]) -> dict[str, Any]:
    frame = pd.DataFrame(payload["rows"])
    frame["datetime"] = pd.to_datetime(frame.pop("date"))
    frame = frame.rename(columns={"symbol": "instrument"}).set_index(["datetime", "instrument"]).sort_index()
    output = {}
    for key in payload["factors"]:
        ic, rank_ic = calc_ic(frame[key], frame["target"])
        output[key] = {
            str(day.date()): {
                "ic": float(ic.loc[day]) if np.isfinite(ic.loc[day]) else None,
                "rank_ic": float(value) if np.isfinite(value) else None,
            }
            for day, value in rank_ic.items()
        }
    return {"status": "available", "version": version("pyqlib"), "analysis": output}


def main() -> None:
    result: dict[str, Any]
    with contextlib.redirect_stdout(sys.stderr):
        if "--diagnose" in sys.argv:
            result = {"status": "available", "version": version("pyqlib"), "capability": "signal_analysis"}
        else:
            payload = json.load(sys.stdin)
            result = {"batches": [analyze_signals(batch) for batch in payload["batches"]]}
    logger.remove()
    logger.add(sys.stdout, format="{message}", colorize=False)
    logger.info(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
