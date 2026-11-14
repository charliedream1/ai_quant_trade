"""Inspectable financial sections reuse one frozen company snapshot."""

import pandas as pd

from src.engine.economics.config import economics_config


def financial_sections(snapshot):
    cfg = economics_config()
    columns = ["Metric", "Period", "Value", "Unit", "Status"]
    if not snapshot or snapshot.get("kind") != "fundamentals":
        return [pd.DataFrame(columns=columns) for _ in cfg["ui"]["financial_sections"]] + [pd.DataFrame(), ""]
    selected = snapshot["selected"]
    definitions = {**cfg["fields"], **cfg["derived"]}
    frames = []
    for keys in cfg["ui"]["financial_sections"].values():
        frames.append(
            pd.DataFrame(
                [
                    {
                        "Metric": definitions[key]["label"],
                        "Period": selected["report_period"],
                        "Value": selected["metrics"].get(key),
                        "Unit": definitions[key]["unit"],
                        "Status": selected["statuses"].get(
                            key, "available" if selected["metrics"].get(key) is not None else "missing"
                        ),
                    }
                    for key in keys
                ],
                columns=columns,
            )
        )
    history = pd.DataFrame([{"Period": row["report_period"], **row["metrics"]} for row in snapshot["periods"]])
    valuation = snapshot.get("valuation", {})
    note = (
        "Selected-period statement summaries; income/cash flows are year-to-date unless explicitly labelled "
        "single-quarter or TTM. Missing values remain unknown. Current valuation: "
        + str(valuation.get("status"))
        + "; quote timestamp: "
        + str(valuation.get("updated_at") or "unavailable")
        + ". Peer comparisons remain in the metric overview; original revisions are available under Sources."
    )
    return [*frames, history, note]
