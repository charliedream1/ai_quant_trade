"""Project-local layout persistence independent of immutable computation versions."""

import json
import math
import re
from typing import Any

from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.strategy.composition.graph_config import graph_config

SCHEMA = """
CREATE TABLE IF NOT EXISTS strategy_graph_layouts (
 layout_key TEXT PRIMARY KEY, definition_digest TEXT NOT NULL, layout TEXT NOT NULL,
 revision INTEGER NOT NULL, updated_at TEXT NOT NULL
);
"""


class GraphLayouts:
    def __init__(self, repo: Repository | None = None):
        self.repo = repo or Repository()
        self.repo.db.executescript(SCHEMA)

    @staticmethod
    def key(value: str) -> str:
        if not re.fullmatch(r"(?:draft:[0-9a-f]{32}|pipeline:[1-9][0-9]*)", value):
            raise ValueError("Invalid layout identity")
        return value

    def load(self, key: str) -> dict[str, Any]:
        row = self.repo.db.query_one("SELECT * FROM strategy_graph_layouts WHERE layout_key=?", (self.key(key),))
        return {**row, "layout": json.loads(row["layout"])} if row else {"layout_key": key, "layout": {}, "revision": 0}

    def save(self, key: str, definition_digest: str, layout: dict, revision: int) -> dict[str, Any]:
        key = self.key(key)
        self.validate(layout)
        if not re.fullmatch(r"[0-9a-f]{64}", definition_digest):
            raise ValueError("Invalid definition digest")
        encoded = json.dumps(layout, ensure_ascii=False, allow_nan=False)
        now = utc_now_iso()
        if revision == 0:
            cursor = self.repo.db.execute(
                "INSERT OR IGNORE INTO strategy_graph_layouts VALUES(?,?,?,?,?)",
                (key, definition_digest, encoded, 1, now),
            )
        else:
            cursor = self.repo.db.execute(
                "UPDATE strategy_graph_layouts SET definition_digest=?,layout=?,revision=revision+1,updated_at=? WHERE layout_key=? AND revision=?",
                (definition_digest, encoded, now, key, revision),
            )
        if cursor.rowcount != 1:
            raise ValueError("Layout changed in another session; reload before saving")
        return self.load(key)

    @staticmethod
    def validate(layout: dict) -> None:
        if not isinstance(layout, dict) or len(json.dumps(layout).encode()) > graph_config()["limits"]["max_bytes"]:
            raise ValueError("Invalid layout payload")

        limits = graph_config()["limits"]
        for scope, item in layout.items():
            if (
                not re.fullmatch(r"main(?:/[A-Za-z][A-Za-z0-9_-]{0,63})*", scope)
                or scope.count("/") > limits["max_layout_depth"]
            ):
                raise ValueError("Invalid layout scope")
            if not isinstance(item, dict) or set(item) - {"positions", "viewport", "selected"}:
                raise ValueError("Invalid layout fields")
            positions = item.get("positions") or {}
            if not isinstance(positions, dict) or len(positions) > limits["max_layout_nodes"]:
                raise ValueError("Invalid layout positions")
            for name, point in positions.items():
                if not isinstance(name, str) or not re.fullmatch(
                    r"(?:@(?:portfolio|risk|execution)|s:[A-Za-z][A-Za-z0-9_-]{0,63}|[A-Za-z][A-Za-z0-9_-]{0,63})", name
                ):
                    raise ValueError("Invalid layout node")
                GraphLayouts.point(point, {"x", "y"})
            if "viewport" in item:
                GraphLayouts.point(item["viewport"], {"x", "y", "zoom"})
                if not limits["min_zoom"] <= item["viewport"]["zoom"] <= limits["max_zoom"]:
                    raise ValueError("Invalid layout zoom")
            if "selected" in item and not isinstance(item["selected"], str):
                raise ValueError("Invalid selection")

    @staticmethod
    def point(point, keys):
        if (
            not isinstance(point, dict)
            or set(point) != keys
            or any(
                isinstance(v, bool)
                or not isinstance(v, (int, float))
                or not math.isfinite(v)
                or abs(v) > graph_config()["limits"]["max_bytes"]
                for v in point.values()
            )
        ):
            raise ValueError("Invalid layout coordinate")
