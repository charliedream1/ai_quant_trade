"""Separate analyst, bull, bear and chair contexts; disagreements remain in the record."""

from .contracts import decisions, opinion


def analyze(session, evidence: dict) -> dict:
    context = {key: evidence[key] for key in ("market", "documents")}
    peers = {}
    for role in session.run["config"]["depth"]["analysts"]:
        peers[role] = opinion(session.role(role, context, "opinion"), context)
    return {"analysts": peers}


def debate(session, evidence: dict, prior: dict) -> dict:
    context = {key: evidence[key] for key in ("market", "documents")}
    peers = dict(prior["analysts"])
    cfg = session.run["config"]
    for turn in range(cfg["depth"]["debate_rounds"]):
        for role in ("bull", "bear"):
            scoped = {**context, "peers": peers.copy()}
            peers[role + ":" + str(turn)] = opinion(session.role(role, scoped, "opinion"), scoped)
    scoped = {**context, "peers": peers}
    verdict = decisions(session.role("chair", scoped, "decision"), scoped)
    if evidence["missing"]:
        for row in verdict["decisions"]:
            if row["action"] == "select":
                row.update(action="watch", score=0.0, reason=cfg["prompts"]["roles"]["chair"] + "；必需证据不足")
    return {
        **prior,
        "roles": peers,
        "decision": verdict,
        "coverage_status": evidence["coverage_status"],
        "can_allocate": not evidence["missing"],
    }
