"""Explicit fixture inbox in an isolated local application; no provider calls."""

import json
from pathlib import Path

import uvicorn
import yaml

from src.api.app import app
from src.core.config import get_settings
from src.notifications.config import target
from src.notifications.store import NotificationStore


def main():
    data = yaml.safe_load(Path(__file__).with_name("fixtures.yaml").read_text(encoding="utf-8"))
    store = NotificationStore()
    state = {}
    for kind in ("warning", "critical"):
        state[kind] = store.publish("fixture", kind, kind, data["title"] + kind, data["message"], target("factor"))[
            "id"
        ]
    get_settings().data_dir.parent.joinpath("browser-seed.json").write_text(json.dumps(state), encoding="utf-8")
    uvicorn.run(app, host="127.0.0.1", port=8890, access_log=False)


if __name__ == "__main__":
    main()
