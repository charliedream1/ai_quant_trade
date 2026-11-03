"""Study creation freezes one policy for both human and machine hypotheses."""

import math
from copy import deepcopy
from typing import Any

from src.agent.providers import provider_snapshot
from src.core.exceptions import BusinessError
from src.core.timeutil import utc_now_iso
from src.engine.execution.config import resolve_costs
from src.strategy.composition.config import config as pipeline_config
from src.strategy.composition.validation import settings as execution_settings
from src.strategy.factors.config import factor_set

from .config import config, digest, invalid, policy, prompts, source_manifest
from .contracts import StudyRequest
from .factors import market_panel, python_source, validate_expression
from .pit import timestamp
from .research import split_dates
from .store import LOCK, AlphaStore


def create_study(store: AlphaStore, request: dict[str, Any]) -> dict[str, Any]:
    request = StudyRequest.model_validate(request).model_dump(exclude_none=True)
    cfg = config()
    mode = request.get("mode", "alpha")
    if mode not in {"alpha", "theme", "regime"}:
        raise invalid("未知研究流程")
    dataset = store.get("alpha_datasets", int(request["dataset_id"]))
    expected = {"alpha": "market", "theme": "documents", "regime": "macro"}[mode]
    if dataset["kind"] != expected:
        raise invalid("研究流程与数据类型不匹配")
    batch = request.get("batch_size", cfg["study_defaults"]["batch_size"])
    if type(batch) is not int or not 1 <= batch <= cfg["limits"]["max_candidates"]:
        raise invalid("候选批次预算不合法")
    policy_overrides = {**({"max_weight": 1.0} if mode == "regime" else {}), **(request.get("policy") or {})}
    settings = {
        "policy": policy(policy_overrides),
        "limits": deepcopy(cfg["limits"]),
        "prompts": deepcopy(prompts()),
        "models": deepcopy(request.get("models") or {}),
        "purpose": str(request.get("purpose") or cfg["study_defaults"]["purpose"]),
        "batch_size": batch,
        "data_digest": dataset["digest"],
        "market": request.get("market", "CN"),
        "historical_model_memory_risk": True,
        "mode": mode,
        "source_manifest": source_manifest(),
        "reference_factors": factor_set(cfg["study_defaults"]["reference_factor_set"]),
    }
    settings.update(
        fields=deepcopy(cfg["fields"]),
        operators=deepcopy(cfg["operators"]),
        execution=execution_settings("execution", request.get("execution")),
    )
    instrument = pipeline_config()["defaults"]["instruments"].get(settings["market"])
    if instrument:
        for key in ("lot_size", "settlement_sessions"):
            if key not in request.get("execution", {}):
                settings["execution"][key] = instrument[key]
    settings["execution_costs"] = resolve_costs(request.get("execution_costs"), settings["execution"])
    budget = request.get("model_call_budget", cfg["study_defaults"]["model_call_budget"])
    if type(budget) is not int or not 1 <= budget <= cfg["limits"]["max_model_calls"]:
        raise invalid("模型调用预算不合法")
    settings["limits"]["max_model_calls"] = budget
    if request.get("memory_dataset_id"):
        memory = store.get("alpha_datasets", request["memory_dataset_id"])
        if memory["kind"] != "documents":
            raise invalid("研究记忆必须是带可得时点的资料")
        settings["memory_dataset_id"] = memory["id"]
    if settings["market"] not in {"CN", "US"}:
        raise invalid("市场必须为CN或US")
    if mode == "alpha":
        if dataset["payload"]["market"] != settings["market"]:
            raise invalid("行情母池与研究市场不一致")
        panel = market_panel(dataset["payload"]["history"])
        settings["splits"] = split_dates(list(panel["close"].index), settings["policy"])
    else:
        settings["cutoff"] = str(request.get("cutoff") or "")
        timestamp(settings["cutoff"])
        if timestamp(settings["cutoff"]) > timestamp(utc_now_iso()):
            raise invalid("研究截止时点不能是未来")
        market_id = request.get("market_dataset_id")
        if market_id:
            market = store.get("alpha_datasets", int(market_id))
            if market["kind"] != "market":
                raise invalid("关联回测数据必须为行情")
            settings["market_dataset_id"] = market["id"]
            settings["market_data_digest"] = market["digest"]
    if mode == "theme":
        settings["theme"] = str(request.get("theme") or settings["purpose"])
        settings["manual_keywords"] = list(request.get("manual_keywords") or [])
    if mode == "regime":
        _regime_settings(settings, request)
    settings["provider_snapshots"] = {
        role: provider_snapshot(selection, probe=selection.get("backend", "api") != "api")
        for role, selection in settings["models"].items()
    }
    stamp = utc_now_iso()
    study = store.insert(
        "alpha_studies",
        {
            "name": str(request.get("name") or settings["purpose"])[:200],
            "mode": mode,
            "dataset_id": dataset["id"],
            "config": settings,
            "digest": digest(settings),
            "status": "draft",
            "result": {},
            "created_at": stamp,
            "updated_at": stamp,
        },
    )
    store.event(
        study["id"],
        "registered",
        {
            "digest": study["digest"],
            "policy": settings["policy"],
            "batch_size": batch,
            "dataset_digest": dataset["digest"],
        },
    )
    return study


def _regime_settings(settings: dict, request: dict) -> None:
    cfg = config()
    configurations = deepcopy(request.get("configurations") or [])
    if not 1 <= len(configurations) <= cfg["limits"]["max_regime_configurations"]:
        raise invalid("请选择1至8个真实模型实验配置")
    identities = [
        (
            row.get("backend", "api"),
            row.get("model_id") if row.get("backend", "api") == "api" else row.get("model_name") or "default",
            row.get("reasoning_effort", ""),
            row.get("enable_thinking"),
        )
        for row in configurations
    ]
    if len(set(identities)) != len(identities) or any(
        row.get("backend", "api") == "api" and not row.get("model_id") for row in configurations
    ):
        raise invalid("体制实验配置缺模型或重复，不能凑数")
    framework = deepcopy(cfg["regime_defaults"])
    supplied = request.get("regime") or {}
    if set(supplied) - set(framework):
        raise invalid("体制配置字段未登记")
    framework.update(supplied)
    if (
        type(framework["min_confidence"]) not in {float, int}
        or not math.isfinite(framework["min_confidence"])
        or not 0 <= framework["min_confidence"] <= 1
    ):
        raise invalid("体制置信门槛必须是0至1的有限数")
    if framework["growth_series"] == framework["inflation_series"]:
        raise invalid("增长和通胀不能使用同一个输入序列")
    for key in ("min_observations", "window_observations", "validity_days"):
        if type(framework[key]) is not int or not 2 <= framework[key] <= cfg["limits"]["max_dates"]:
            raise invalid("体制窗口、最少观察或有效期不合法")
    if framework["window_observations"] < framework["min_observations"]:
        raise invalid("体制窗口小于最少观察数")
    if (
        set(framework["benchmark_weights"]) != {"equity", "bond"}
        or any(
            type(value) not in {int, float} or not 0 <= value <= 1 for value in framework["benchmark_weights"].values()
        )
        or sum(framework["benchmark_weights"].values()) > 1
    ):
        raise invalid("股债基准配置不合法")
    if type(framework["lag_days"]) is not int or framework["lag_days"] < 1:
        raise invalid("宏观数据必须有正滞后")
    mapping = request.get("asset_mapping") or {}
    if set(mapping) != {"equity", "bond"} or len(set(mapping.values())) != len(mapping):
        raise invalid("请指定不同的可交易股、债资产标识")
    for regime in cfg["regimes"]:
        weights = framework["allocations"].get(regime)
        if (
            not isinstance(weights, dict)
            or set(weights) - set(mapping)
            or any(type(value) not in {float, int} or not 0 <= value <= 1 for value in weights.values())
            or sum(weights.values()) > 1
        ):
            raise invalid("冻结体制配置必须非负且总权重不超过1")
    cutoffs = request.get("decision_dates") or [settings["cutoff"]]
    if not 1 <= len(cutoffs) <= cfg["limits"]["max_regime_observations"]:
        raise invalid("体制决策日期数量不合法")
    if any(timestamp(value) > timestamp(settings["cutoff"]) for value in cutoffs):
        raise invalid("体制决策日期超过研究截止时点")
    settings["configuration_providers"] = [
        provider_snapshot(row, probe=row.get("backend", "api") != "api") for row in configurations
    ]
    effective = [
        (
            row["backend"],
            row.get("base_url"),
            row["model_name"],
            row.get("reasoning_effort"),
            row.get("enable_thinking"),
        )
        for row in settings["configuration_providers"]
        if row.get("configuration_available") is not False and row.get("model_name")
    ]
    if len(set(effective)) != len(effective):
        raise invalid("体制配置对应相同的实际后端/模型/推理设置，不能用不同平台ID凑数")
    settings.update(
        configurations=configurations, regime=framework, asset_mapping=mapping, decision_dates=sorted(set(cutoffs))
    )


def add_candidate(store: AlphaStore, study_id: int, hypothesis: dict, implementation: dict, origin: str) -> dict:
    with LOCK, store.repo.db.transaction():
        study = store.get("alpha_studies", study_id)
        if study["mode"] != "alpha" or study["status"] not in {"draft", "discovering", "discovered"}:
            raise invalid("研究家族已冻结，不能追加或替换候选")
        if len(store.list("alpha_candidates", study_id)) >= study["config"]["batch_size"]:
            raise invalid("预登记候选预算已用完")
        if origin not in {"human", "ai"}:
            raise invalid("假设来源不合法")
        failure = candidate_failure(study, hypothesis, implementation)
        row = store.insert(
            "alpha_candidates",
            {
                "study_id": study_id,
                "origin": origin,
                "hypothesis": hypothesis,
                "implementation": implementation,
                "digest": digest([hypothesis, implementation]),
                "status": "technical_failed" if failure else "implemented",
                "created_at": utc_now_iso(),
            },
        )
        store.event(
            study_id,
            "candidate",
            {"candidate_id": row["id"], "origin": origin, "digest": row["digest"], "failure": failure},
        )
        store.write(study_id, f"candidate-{row['id']}.json", row)
        if not failure:
            store.write(study_id, f"candidate-{row['id']}.py", python_source(implementation["expression"]))
        return row


def candidate_failure(study: dict, hypothesis: dict, implementation: dict) -> str:
    try:
        required = {"title", "mechanism", "counter_hypothesis", "direction", "horizon", "fields", "failure_condition"}
        if not required <= set(hypothesis) or not all(str(hypothesis[key]).strip() for key in required):
            raise invalid("假设缺少预先经济机制、反假设或可证伪条件")
        expression = implementation.get("expression")
        if not isinstance(expression, dict):
            raise invalid("Implementer没有给出受控算子对象")
        fields = validate_expression(expression)
        if fields != set(hypothesis["fields"]) or fields != set(implementation.get("fields") or []):
            raise invalid("实现字段与原假设不一致")
        if (
            type(hypothesis["direction"]) is not int
            or hypothesis["direction"] not in {-1, 1}
            or implementation.get("direction") != hypothesis["direction"]
            or hypothesis["horizon"] != study["config"]["policy"]["horizon"]
            or implementation.get("horizon") != hypothesis["horizon"]
            or not implementation.get("alignment")
        ):
            raise invalid("实现方向、持有期或对齐说明与原假设不一致")
        return ""
    except (BusinessError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return str(exc)
