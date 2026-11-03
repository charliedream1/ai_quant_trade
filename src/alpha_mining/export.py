"""Only reviewed frozen evidence can create a strategy-workshop draft."""

from src.strategy.composition.store import PipelineStore

from .approvals import require_approved
from .backtest import plan_definition
from .config import digest, invalid
from .store import AlphaStore


def export_draft(store: AlphaStore, study_id: int, candidate_id: int | None = None, configuration: int = 1) -> dict:
    study = store.get("alpha_studies", study_id)
    candidate = store.get("alpha_candidates", int(candidate_id or 0)) if study["mode"] == "alpha" else None
    if candidate and candidate["study_id"] != study_id:
        raise invalid("候选不属于该研究")
    require_approved(store, study, candidate)
    cfg, result = study["config"], study["result"]
    market_id = study["dataset_id"] if candidate else cfg.get("market_dataset_id")
    if not market_id:
        raise invalid("导出需明确对应可交易行情母池")
    dataset = store.get("alpha_datasets", market_id)
    symbols = sorted(dataset["payload"]["history"])
    definition = plan_definition(study, candidate["id"] if candidate else 1, symbols)
    definition["name"] = study["name"] + " · 研究草稿"
    if candidate:
        definition["nodes"][0]["params"]["artifact_digest"] = candidate["digest"]
    elif study["mode"] == "theme":
        definition["nodes"][0].update(
            component="alpha_theme", params={"study_id": study_id, "artifact_digest": digest(result)}
        )
    else:
        if not 1 <= configuration <= len(cfg["configurations"]):
            raise invalid("体制实验配置不存在")
        definition["universe"]["symbols"] = list(cfg["asset_mapping"].values())
        definition["nodes"][0].update(
            component="alpha_regime",
            params={"study_id": study_id, "configuration": configuration, "artifact_digest": digest(result)},
        )
        definition["portfolio"] = {
            "component": "regime_fixed",
            "params": {"top_k": len(cfg["asset_mapping"]), "max_weight": cfg["policy"]["max_weight"]},
        }
    definition["description"] = "研究产物；历史LLM回放存在模型记忆风险。先发布新版本并进行前向模拟，不自动实盘。"
    draft = PipelineStore(repo=store.repo).save_draft(definition)
    store.event(
        study_id,
        "exported_draft",
        {"pipeline_id": draft["id"], "candidate_id": candidate_id, "automatic_live_trading": False},
    )
    return {
        "pipeline_id": draft["id"],
        "definition": definition,
        "href": "/app/?module=strategy&view=workshop",
        "automatic_live_trading": False,
    }
