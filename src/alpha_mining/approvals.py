"""Two explicit human tracks supplement, and never replace, deterministic evidence."""

from src.core.timeutil import utc_now_iso

from .config import digest, invalid, source_manifest
from .store import LOCK, AlphaStore


def approve(
    store: AlphaStore, study_id: int, candidate_id: int | None, track: str, decision: str, reviewer: str, evidence: dict
) -> dict:
    if track not in {"economic", "technical"} or decision not in {"approve", "reject"}:
        raise invalid("复核轨道或决定不合法")
    if not reviewer.strip() or not str(evidence.get("reason") or "").strip():
        raise invalid("必须填写实际复核者及复核依据")
    with LOCK, store.repo.db.transaction():
        study = store.get("alpha_studies", study_id)
        if study["status"] not in {"reviewed", "completed"}:
            raise invalid("研究未完成，不能提前复核")
        candidate_digest = digest(study["result"])
        if study["mode"] == "alpha":
            candidate = store.get("alpha_candidates", int(candidate_id or 0))
            final = study["result"].get("final") or {}
            if candidate["study_id"] != study_id or final.get("candidate_id") != candidate_id:
                raise invalid("只能复核完成最终留出的候选")
            if decision == "approve" and not final.get("passed"):
                raise invalid("人工不能覆盖未通过的硬门槛")
            candidate_digest = candidate["digest"]
        elif decision == "approve" and not study["result"].get("export_ready"):
            raise invalid("主题/PIT/真实模型证据不足，不能导出")
        row = store.insert(
            "alpha_reviews",
            {
                "study_id": study_id,
                "candidate_id": candidate_id,
                "track": track,
                "decision": decision,
                "reviewer": reviewer,
                "evidence": evidence,
                "candidate_digest": candidate_digest,
                "created_at": utc_now_iso(),
            },
        )
        store.event(
            study_id, "human_review", {**row, "identity_assurance": "local_operator_not_independent_two_person_auth"}
        )
        return row


def require_approved(store: AlphaStore, study: dict, candidate: dict | None = None) -> None:
    if study["config"]["source_manifest"] != source_manifest():
        raise invalid("冻结研究实现已改变，旧产物不能继续晋级")
    reviews = store.list("alpha_reviews", study["id"])
    expected = candidate["digest"] if candidate else digest(study["result"])
    selected = {}
    for row in sorted(reviews, key=lambda item: item["id"]):
        if row["candidate_id"] == (candidate["id"] if candidate else None) and row["candidate_digest"] == expected:
            selected[row["track"]] = row["decision"]
    if selected != {"economic": "approve", "technical": "approve"}:
        raise invalid("需要相同冻结产物的经济与技术两轨人工通过")
    if not store.verify_events(study["id"]):
        raise invalid("试验事件摘要链校验失败")
    if candidate:
        final = study["result"].get("final") or {}
        if not final.get("passed") or final.get("candidate_id") != candidate["id"]:
            raise invalid("候选没有通过最终冻结验证")
        if final.get("data_is_mock") or not final.get("source", {}).get("verified"):
            raise invalid("演示政策不能把合成或未核验资料导出为生产候选")
    elif not study["result"].get("export_ready"):
        raise invalid("该研究没有可导出的冻结证据")
