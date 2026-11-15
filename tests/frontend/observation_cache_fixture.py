"""Independent process exercising the same JSON source-cache boundary as homepage reads."""

import json
from pathlib import Path


def acquire(data_dir, connection):
    from src.core import config
    from src.core.config import Settings
    from src.frontend.service.shared_observations import shared_observation

    root = Path(data_dir)
    config._SETTINGS = Settings(data_dir=root, db_path=root / "app.db", data_mode="mock")

    def fetch():
        with (root / "acquisitions.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"observed": True}) + "\n")
        return {"source": "declared test observation", "value": 7}

    try:
        connection.send(shared_observation("same-source", fetch))
    finally:
        connection.close()
