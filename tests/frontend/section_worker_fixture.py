"""Block one source until the browser verifies that an earlier section is visible."""

import os
import sys
from functools import partial
from pathlib import Path
from threading import Event


class Quotes:
    def __init__(self, root):
        self.root = root

    def indices(self, refresh=False):
        return [{"code": "declared", "name": "Visible before sector completion", "price": 123.0, "change_pct": 1.2}]

    def sector_rankings(self, **kwargs):
        (self.root / "sector-waiting").touch()
        while not (self.root / "release-sector").exists():
            Event().wait(0.05)
        if (self.root / "fail-sector").exists() and (self.root / "fail-sector").read_text(encoding="utf-8") == "fail":
            raise ValueError("Declared sector failure; the completed index remains available")
        return [{"code": "sector", "name": "Released sector", "change_pct": -1.0, "ranking": "decliners"}]


def serve(connection):
    if sys.platform != "win32":
        os.setsid()
    from src.frontend.read_worker import invoke, transferable
    from src.frontend.service import market

    original = market.QuoteService
    while True:
        try:
            request = connection.recv()
        except EOFError:
            return
        if request is None:
            return
        root = Path(request[3].data_dir)
        if request[0] == "market_overview":
            market.QuoteService = partial(Quotes, root)
        try:
            success, value = invoke(
                request, lambda index, value: connection.send(("panel", index, transferable(value)))
            )
            connection.send((success, value))
        finally:
            market.QuoteService = original
