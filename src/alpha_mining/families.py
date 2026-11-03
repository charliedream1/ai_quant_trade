"""Repeated validation on overlapping known outcomes is exploration, never a fresh gate."""

from src.core.repository import json_loads

from .config import invalid
from .store import AlphaStore


def check_unseen_validation(store: AlphaStore, study: dict) -> None:
    days = study["config"]["splits"]["validation"]
    symbols = set(store.get("alpha_datasets", study["dataset_id"])["payload"]["history"])
    consumed = store.repo.db.query(
        "SELECT DISTINCT s.* FROM alpha_studies s LEFT JOIN alpha_trials t ON t.study_id=s.id WHERE s.id<>? AND (t.split IN ('validation','holdout') OR s.status IN ('validating','testing'))",
        (study["id"],),
    )
    for row in consumed:
        cfg = json_loads(row["config"], {})
        if cfg.get("market") != study["config"]["market"]:
            continue
        prior = cfg.get("splits", {}).get("validation", [])
        prior_holdout = cfg.get("splits", {}).get("holdout", [])
        if set(days) & set(prior + prior_holdout):
            earlier = store.get("alpha_datasets", row["dataset_id"])
            if symbols & set(earlier["payload"].get("history", {})):
                raise invalid("重叠证券/日期的验证已被读取，不能换项目重新宣称未见验证；请使用新数据")
