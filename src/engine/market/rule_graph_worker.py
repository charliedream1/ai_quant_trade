"""One disposable worker builds a rule graph and atomically saves checkpoints."""

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

from src.core.config import get_settings
from src.core.redaction import redact_text
from src.data import DataSourceManager, SecurityMasterService

from .relation_graph import RelationGraphService
from .rule_graph_progress import OBSERVER, SELECTED


def write_json(path, value):
    pending = path.with_name(uuid4().hex + ".pending")
    pending.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    os.replace(pending, path)


def main():
    folder = Path(sys.argv[1]).resolve()
    base = (get_settings().data_dir / "rule_graph_runs").resolve()
    if not folder.is_relative_to(base):
        raise ValueError("Rule worker path is outside configured storage")
    request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
    symbol = SecurityMasterService().resolve_symbol(request["symbol"], request["market"])
    service = RelationGraphService(data=DataSourceManager(market=request["market"]))

    def checkpoint(graph, stage):
        normalized = service._finalize_graph(graph, symbol, request["relation_types"] or None)
        normalized.update(mode="rules", market=request["market"], symbol=symbol, stage=stage)
        write_json(folder / "checkpoint.json", normalized)

    OBSERVER.set(checkpoint)
    SELECTED.set(set(request["relation_types"]))
    try:
        result = service.graph(symbol, request["relation_types"] or None, request["depth"])
        result["source_partial"] = bool(result.get("source_gaps")) or not result.get("edges")
        result.update(mode="rules", market=request["market"], symbol=symbol, stage="Complete")
        write_json(folder / "completed.json", result)
    except Exception as exc:
        write_json(folder / "failure.json", {"error": type(exc).__name__, "message": redact_text(str(exc))[:500]})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
