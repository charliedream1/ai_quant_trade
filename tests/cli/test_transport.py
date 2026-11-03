"""A real HTTP peer validates failure envelopes, bounds and no mutation retries."""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from src.cli.client import Client
from src.cli.config import load_config
from src.cli.errors import CliError, ExitCode, result_exit
from src.cli.parser import parse


@pytest.fixture()
def peer():
    state = {"posts": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def do_POST(self):
            state["posts"] += 1
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if self.path.endswith("/timeout"):
                threading.Event().wait(0.2)
                return
            if self.path.endswith("/html"):
                self.wfile.write(b"<html>Proxy login</html>")
            elif self.path.endswith("/large"):
                self.wfile.write(b"x" * 2000)
            elif self.path.endswith("/bad-envelope"):
                self.wfile.write(b'{"ok":true}')
            else:
                self.wfile.write(b'{"code":0,"message":"","data":{"status":"failed"}}')

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    options, _, _ = parse(["--base-url", f"http://127.0.0.1:{server.server_port}", "system", "info"])
    config = load_config(options)
    config["limits"]["response_bytes"] = 1000
    config["timeouts"].update(read=2, long_read=2)
    client = Client(config)
    try:
        yield client, state
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize("path", ["html", "large", "bad-envelope"])
def test_invalid_responses_are_transport_errors_without_retry(peer, path):
    client, state = peer
    with pytest.raises(CliError) as failure:
        client.request({"method": "POST", "path": "/" + path, "body": {}, "query": {}}, execution=True)
    assert failure.value.exit_code == ExitCode.TRANSPORT
    assert state["posts"] == 1


def test_http_200_does_not_hide_failed_execution(peer):
    client, state = peer
    result = client.request({"method": "POST", "path": "/failed", "body": {}, "query": {}}, execution=True)
    assert result_exit(result, execution=True) == ExitCode.BUSINESS
    assert state["posts"] == 1


def test_read_timeout_has_unknown_outcome_and_no_retry(peer):
    client, state = peer
    client.config["timeouts"].update(read=0.05, long_read=0.05)
    with pytest.raises(CliError) as failure:
        client.request({"method": "POST", "path": "/timeout", "body": {}, "query": {}}, execution=True)
    assert failure.value.exit_code == ExitCode.TIMEOUT
    assert failure.value.meta["outcome"] == "unknown"
    assert failure.value.meta["mutation_may_have_completed"] is True
    assert state["posts"] == 1
