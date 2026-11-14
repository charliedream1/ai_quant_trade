"""Controlled blocking source inside real owned workers; never enabled in production."""

import json
import os
from pathlib import Path
from threading import Event

import requests
from filelock import FileLock


def serve(connection):
    if os.name != "nt":
        os.setsid()
    while True:
        try:
            request = connection.recv()
        except EOFError:
            return
        if request is None:
            return
        name, args, kwargs, settings, market = request
        folder = Path(settings.data_dir)
        if name in {"economic_load", "graph_read"} or (name == "stock" and args[0] == "SLOW"):
            folder.mkdir(parents=True, exist_ok=True)
            with FileLock(str(folder / "source.lock")):
                (folder / "worker-started.json").write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
                endpoint = folder / "slow-source-url.txt"
                if endpoint.exists():
                    requests.get(endpoint.read_text(encoding="utf-8"), timeout=120)
                else:
                    Event().wait(120)
                connection.send((True, "obsolete result"))
        elif name == "home_news":
            with FileLock(str(folder / "source.lock")):
                (folder / "worker-started.json").write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
                while not (folder / "release-source").exists():
                    Event().wait(0.05)
                connection.send((True, "shared result"))
        else:
            from src.frontend.read_worker import invoke

            connection.send(invoke(request))
