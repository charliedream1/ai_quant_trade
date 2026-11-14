"""Run the actual financial callback with explicit accounting fixtures inside its worker."""

import copy
import json
import os
import sys


def failure_formatter(path, original):
    def format_failure(exc):
        path.write_text(json.dumps({"type": type(exc).__name__, "message": str(exc)}), encoding="utf-8")
        return original(exc)

    return format_failure


def financial_source(observations):
    def fetch(self, name, *, symbol="", refresh=False):
        if not symbol:
            raise AssertionError("This browser fixture permits only declared financial statements")
        result = copy.deepcopy(observations[name])
        for row in result["rows"]:
            row["SECURITY_CODE"] = symbol.split(".")[0]
        return result

    return fetch


def serve(connection):
    if sys.platform != "win32":
        os.setsid()
    from src.data.economics import EconomicDataSource
    from src.frontend.common import errors
    from src.frontend.read_worker import invoke

    original = EconomicDataSource.fetch
    original_format = errors.ui_error_message
    while True:
        try:
            request = connection.recv()
        except EOFError:
            return
        if request is None:
            return
        name, _, _, settings, _ = request
        with (settings.data_dir / "economic-worker-methods.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"method": name}) + "\n")
        if name == "economic_load":
            (settings.data_dir / "economic-worker-arguments.json").write_text(json.dumps(request[1]), encoding="utf-8")
            observations = json.loads((settings.data_dir / "economic-observations.json").read_text(encoding="utf-8"))

            EconomicDataSource.fetch = financial_source(observations)
            errors.ui_error_message = failure_formatter(
                settings.data_dir / "economic-worker-failure.json", original_format
            )
        try:
            connection.send(invoke(request))
        finally:
            EconomicDataSource.fetch = original
            errors.ui_error_message = original_format
