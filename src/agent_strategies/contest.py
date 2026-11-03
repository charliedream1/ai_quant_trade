"""Information and capital contests use matured utilities, never persuasive votes as returns."""

from collections import Counter

from .contracts import decisions, observations
from .predict import predict
from .scores import records
from .shadow import target_weights


def similarity(left: str, right: str) -> float:
    a, b = Counter(zip(left, left[1:], strict=False)), Counter(zip(right, right[1:], strict=False))
    norm = sum(v * v for v in a.values()) ** 0.5 * sum(v * v for v in b.values()) ** 0.5
    return sum(value * b.get(key, 0) for key, value in a.items()) / norm if norm else float(left == right)


def utilities(session, channel: str) -> dict:
    run = session.run
    past = records(session.store, run["lineage"], channel, run["as_of"])
    return {
        actor: predict(
            rows, run["config"], session.store.artifact(run["id"], "utility-" + channel + "-" + actor + ".txt")
        )
        for actor, rows in past.items()
    }


def select_information(observed: list[dict], forecasts: dict, cfg: dict) -> dict:
    picked: list[dict] = []
    dropped: list[dict] = []
    used = 0
    warmup = not forecasts or all(row["status"] in {"cold", "insufficient_training"} for row in forecasts.values())
    ordered = sorted(observed, key=lambda row: (-float(forecasts.get(row["actor"], {}).get("utility") or 0), row["id"]))
    for row in ordered:
        forecast = forecasts.get(row["actor"], {})
        utility = forecast.get("utility")
        reason = "selected"
        if not warmup and (utility is None or utility <= 0):
            reason = "non_positive_or_unavailable_utility"
        elif used + len(row["text"]) + len(row.get("quote", "")) > cfg["limits"]["context_chars"]:
            reason = "context_budget"
        elif any(
            row["symbol"] == prior["symbol"]
            and row.get("direction") == prior.get("direction")
            and (
                (row["source_id"], row.get("quote_id") or row.get("quote") or row["text"])
                == (prior["source_id"], prior.get("quote_id") or prior.get("quote") or prior["text"])
                or similarity(row["text"], prior["text"]) >= cfg["policy"]["similarity_limit"]
            )
            for prior in picked
        ):
            reason = "redundant_evidence"
        if reason == "selected":
            picked.append(row)
            used += len(row["text"]) + len(row.get("quote", ""))
        else:
            dropped.append({"id": row["id"], "reason": reason})
    return {
        "selected": picked,
        "dropped": dropped,
        "context_chars": used,
        "warmup": warmup,
        "selection_method": "deterministic_budgeted_dedup_not_paper_submodular_optimizer",
    }


def data_team(session, evidence: dict) -> dict:
    context = {key: evidence[key] for key in ("market", "documents")}
    observed = []
    for actor in session.run["config"]["depth"]["data_roles"]:
        observed.extend(observations(session.role(actor, context, "observations"), context, actor))
    forecasts = utilities(session, "data")
    selected = select_information(observed, forecasts, session.run["config"])
    session.event("data_contest", {"forecasts": forecasts, **selected})
    return {"observations": observed, "data_forecasts": forecasts, "information": selected}


def research_team(session, evidence: dict, prior: dict) -> dict:
    selected = prior["information"]["selected"]
    source_ids = {row["source_id"] for row in selected}
    context = {
        "market": evidence["market"],
        "documents": {k: v for k, v in evidence["documents"].items() if k in source_ids},
        "factors": selected,
    }
    proposals = {}
    cfg = session.run["config"]
    for actor in cfg["depth"]["beliefs"]:
        proposals[actor] = decisions(session.role(actor, context, "decision"), context)
    aliases = {"P" + str(index + 1): actor for index, actor in enumerate(sorted(proposals))}
    judged_context = {
        "market": evidence["market"],
        "proposals": {key: proposals[actor] for key, actor in aliases.items()},
    }
    quality = session.role("judge", judged_context, "quality")
    ratings = quality.get("ratings")
    if (
        not isinstance(ratings, list)
        or {row.get("proposal") for row in ratings} != set(aliases)
        or len(ratings) != len(aliases)
    ):
        raise ValueError("匿名质量评审遗漏或伪造提案")
    for row in ratings:
        value = row.get("quality")
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0 <= value <= 1
            or not row.get("reason")
        ):
            raise ValueError("质量评分或理由不合法")
    forecasts = utilities(session, "research")
    strengths = {
        actor: float(row["utility"])
        for actor, row in forecasts.items()
        if actor in proposals and row.get("utility") is not None and row["utility"] > 0 and row.get("mean", 0) > 0
    }
    total = sum(strengths.values())
    budgets = {
        actor: min(cfg["policy"]["max_actor_budget"], strengths.get(actor, 0) / total) if total else 0.0
        for actor in proposals
    }
    if evidence["missing"] or not selected:
        budgets = dict.fromkeys(proposals, 0.0)
    targets: dict[str, float] = {}
    for actor, proposal in proposals.items():
        for symbol, weight in target_weights(proposal, cfg["policy"]["max_actor_budget"]).items():
            targets[symbol] = targets.get(symbol, 0) + budgets[actor] * weight
    targets = {symbol: weight for symbol, weight in targets.items() if weight > 0}
    decision = {
        "summary": "成熟成绩决定预算；质量评审不覆盖负效用",
        "decisions": [
            {
                "symbol": symbol,
                "action": "select" if targets.get(symbol, 0) > 0 else "watch",
                "score": targets.get(symbol, 0),
                "horizon": cfg["policy"]["horizon"],
                "reason": "double_contest_budget" if total else "cold_or_non_positive_utility",
                "evidence_ids": ["market"],
            }
            for symbol in evidence["market"]["candidates"]
        ],
    }
    result = {
        **prior,
        "proposals": proposals,
        "quality": quality,
        "research_forecasts": forecasts,
        "budgets": budgets,
        "targets": targets,
        "decision": decision,
        "cash": 1 - sum(targets.values()),
        "cold_start": not strengths,
        "can_allocate": bool(targets),
        "coverage_status": evidence["coverage_status"],
    }
    session.event(
        "research_contest",
        {k: v for k, v in result.items() if k in {"budgets", "targets", "cash", "cold_start", "research_forecasts"}},
    )
    return result
