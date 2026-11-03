"""User imports and existing server archives have separately recorded provenance."""

import csv
import io
import json
from typing import Any

import yaml

from src.engine.composition.data import load_snapshot

from .config import config, invalid


def parse_upload(kind: str, name: str, content: bytes) -> dict[str, Any]:
    if len(content) > config()["limits"]["max_upload_bytes"]:
        raise invalid("导入文件过大")
    try:
        text = content.decode("utf-8-sig")
        if name.lower().endswith(".json"):
            result = json.loads(text)
        elif name.lower().endswith((".yaml", ".yml")):
            result = yaml.safe_load(text)
        elif name.lower().endswith(".csv"):
            result = csv_payload(kind, list(csv.DictReader(io.StringIO(text))))
        else:
            raise invalid("研究导入仅支持UTF-8 CSV、JSON或YAML")
    except (UnicodeError, ValueError, yaml.YAMLError) as exc:
        raise invalid("导入文件编码或格式错误") from exc
    if not isinstance(result, dict):
        raise invalid("研究数据必须为对象")
    return result


def csv_payload(kind: str, rows: list[dict]) -> dict:
    if not rows:
        raise invalid("模板只有列名，请填写真实资料后导入")
    if kind == "market":
        history: dict[str, list] = {}
        for row in rows:
            if not row.get("symbol"):
                raise invalid("行情CSV缺少symbol")
            values = {key: value for key, value in row.items() if value and key != "symbol"}
            history.setdefault(row["symbol"], []).append(values)
        return {"history": history, "source": "user_csv", "price_adjustment": "unknown", "is_mock": False}
    if kind == "documents":
        for row in rows:
            row["symbols"] = [value.strip() for value in str(row.get("symbols") or "").split("|") if value.strip()]
        return {"documents": rows, "source": "user_csv", "is_mock": False}
    return {"observations": rows, "source": "user_csv", "is_mock": False}


def register_snapshot(service, snapshot_id: str) -> dict:
    snapshot = load_snapshot({"snapshot_id": snapshot_id}, {}, lambda *args: None)
    return service.register_dataset(
        "归档行情 " + snapshot_id[:12],
        "market",
        snapshot,
        {
            "verified": not snapshot["is_mock"],
            "method": "existing_server_snapshot_sha256",
            "snapshot_id": snapshot_id,
            "source": snapshot["source"],
        },
    )


def attest(service, dataset_id: int, reviewer: str, evidence: dict) -> dict:
    if not reviewer.strip() or not evidence.get("reason") or not evidence.get("source_reference"):
        raise invalid("资料核验需要复核者、核验理由和来源引用")
    original = service.store.get("alpha_datasets", dataset_id)
    # A new row prevents retroactively changing the provenance of registered studies.
    return service.register_dataset(
        original["name"],
        original["kind"],
        original["payload"],
        {
            "verified": True,
            "method": "local_operator_attestation_not_independent_certification",
            "reviewer": reviewer,
            "evidence": evidence,
            "original_dataset_id": dataset_id,
            "original_digest": original["digest"],
        },
    )
