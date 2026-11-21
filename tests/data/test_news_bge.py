"""Explicit installation consent, integrity, and local endpoint compatibility."""

import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace

import pytest

from src.engine.market import news_bge, news_bge_install


def test_installer_preview_treats_eof_as_no_consent(monkeypatch, tmp_path):
    def closed_input(*args):
        raise EOFError

    monkeypatch.setattr(news_bge_install.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr("builtins.input", closed_input)
    monkeypatch.setattr(news_bge_install, "install", lambda *args, **kwargs: pytest.fail("Download performed"))
    assert news_bge_install.main(["--target", str(tmp_path / "model")]) == 0
    assert not (tmp_path / "model").exists()


def test_decline_then_install_validated_assets(monkeypatch, tmp_path):
    payload = b"Declared fixture, never a downloaded model"
    cfg = {"assets": {"model.onnx": {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}}}
    downloads = []
    monkeypatch.setattr(news_bge_install, "config", lambda: cfg)
    monkeypatch.setattr(news_bge_install, "local_vectors", lambda *args: [[1.0, 0.0]])

    def fetch(name, destination, config):
        downloads.append(name)
        (destination / name).write_bytes(payload)

    monkeypatch.setattr(news_bge_install, "_fetch", fetch)
    model = tmp_path / "model"
    assert news_bge_install.install(model) is False
    assert not model.exists() and not downloads
    assert news_bge_install.install(model, confirmed=True)
    assert (model / "model.onnx").read_bytes() == payload
    assert news_bge_install.install(model, confirmed=True)
    assert downloads == ["model.onnx"]
    (model / "model.onnx").write_bytes(b"wrong")
    with pytest.raises(ValueError, match="size"):
        news_bge_install.install(model, confirmed=True)


def test_remote_embeddings_use_bearer_and_return_ranked_phrases(monkeypatch):
    observed = []

    class Endpoint(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):  # noqa: N802
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            observed.append((self.headers.get("Authorization"), self.path, body))
            vectors = [[1, 0], [0, 1], [0, 1], [0, 1]]
            response = json.dumps({"data": [{"index": i, "embedding": v} for i, v in enumerate(vectors)]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Endpoint)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("ALL_IN_ONE_NEWS_BGE_MODE", "remote")
    monkeypatch.setenv("ALL_IN_ONE_NEWS_BGE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("ALL_IN_ONE_NEWS_BGE_API_KEY", "declared-fixture-bearer")
    ranked = [
        {"keyword": "城市更新", "weight": 0.51, "headline": "市场报道一"},
        {"keyword": "先进封装", "weight": 0.49, "headline": "市场报道二"},
    ]
    try:
        rows, method = news_bge.rerank(ranked)
        assert rows[0]["keyword"] == "先进封装" and "远程" in method
        assert observed[0][0] == "Bearer declared-fixture-bearer"
        assert observed[0][1] == "/v1/embeddings"
        assert observed[0][2]["input"] == ["城市更新", "先进封装", "市场报道一", "市场报道二"]
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
