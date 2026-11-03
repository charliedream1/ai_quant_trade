"""Idempotent delayed score updates; future prices are never read at the decision point."""

import json

from src.alpha_mining.pit import timestamp

from .evidence import cutoff
from .shadow import shadow_book, target_weights
from .store import LOCK


def mature(store, current: dict, frame) -> list[dict]:
    cfg = current["config"]
    rows = store.repo.db.query(
        "SELECT id FROM agent_strategy_runs WHERE lineage=? AND as_of<? AND status='completed' ORDER BY as_of,id LIMIT ?",
        (current["lineage"], frame.as_of, cfg["limits"]["max_history_runs"]),
    )
    updates = []
    now = timestamp(cutoff(frame.as_of))
    for record in rows:
        run = store.get(record["id"])
        days = sorted({row["date"] for rows in frame.history.values() for row in rows if row["date"] > run["as_of"]})
        horizon = run["config"]["policy"]["horizon"]
        if len(days) <= horizon or timestamp(cutoff(days[horizon])) >= now:
            continue
        end, effective = days[horizon], cutoff(days[horizon])
        history = {s: [dict(row) for row in rows if row["date"] <= end] for s, rows in frame.history.items()}
        pending = [("research", actor, proposal) for actor, proposal in run["result"].get("proposals", {}).items()]
        pending += [
            ("data", actor, None) for actor in sorted({r["actor"] for r in run["result"].get("observations", [])})
        ]
        for channel, actor, proposal in pending:
            exists = store.repo.db.scalar(
                "SELECT COUNT(*) FROM agent_strategy_scores WHERE run_id=? AND actor=? AND channel=?",
                (run["id"], actor, channel),
            )
            if exists:
                continue
            if channel == "research":
                weights = target_weights(proposal, cfg["policy"]["max_actor_budget"])
                detail = shadow_book(run, history, [run["as_of"], *days[: horizon + 1]], weights)
                value = detail["net_excess"]
                detail["artifact"] = "shadow-" + actor + ".json"
                store.write(run["id"], detail["artifact"], detail)
                detail = {key: val for key, val in detail.items() if key not in {"orders", "trades"}}
            else:
                values = []
                for observation in run["result"].get("observations", []):
                    if observation["actor"] != actor:
                        continue
                    bars = {row["date"]: row for row in history.get(observation["symbol"], [])}
                    if days[0] not in bars or end not in bars:
                        continue
                    values.append(observation["direction"] * (bars[end]["open"] / bars[days[0]]["open"] - 1))
                if not values:
                    continue
                value = sum(values) / len(values)
                detail = {"scope": "directional_return_proxy_not_account_pnl", "observations": len(values)}
            detail.update(label_end=end, entry=days[0], effective_at=effective)
            with LOCK, store.repo.db.transaction():
                store.repo.db.execute(
                    "INSERT OR IGNORE INTO agent_strategy_scores(run_id,lineage,actor,channel,value,effective_at,evidence) VALUES(?,?,?,?,?,?,?)",
                    (
                        run["id"],
                        current["lineage"],
                        actor,
                        channel,
                        value,
                        effective,
                        json.dumps(detail, ensure_ascii=False),
                    ),
                )
            updates.append(
                {"run_id": run["id"], "actor": actor, "channel": channel, "value": value, "effective_at": effective}
            )
    return updates


def records(store, lineage: str, channel: str, as_of: str) -> dict[str, list[dict]]:
    rows = store.repo.db.query(
        "SELECT * FROM agent_strategy_scores WHERE lineage=? AND channel=? AND effective_at<? ORDER BY effective_at,id",
        (lineage, channel, cutoff(as_of)),
    )
    result: dict[str, list[dict]] = {}
    for row in rows:
        result.setdefault(row["actor"], []).append(row)
    return result
