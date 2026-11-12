"""Explicit deterministic HTTP fixtures for decisions, reranking and generation."""

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@contextmanager
def scoring_server(values):
    state = {"requests": [], "fail": set(), "invalid": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            return

        def do_POST(self):  # noqa: N802
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["requests"].append((self.path, body))
            if self.path in state["fail"]:
                return self.reply(503, {})
            if self.path == "/decisions":
                answers = {key: {"type": "noul", "noul": 0.9} for key in body["questions"]}
                if state["invalid"]:
                    answers = {"foreign": {"type": "noul", "noul": 0.9}}
                return self.reply(200, {"model": "protocol-fixture", "answers": answers})
            if self.path == "/rerank":
                return self.reply(
                    200,
                    {"results": [{"index": i, "relevance_score": 1 / (i + 1)} for i in range(len(body["documents"]))]},
                )
            if self.path == "/embeddings":
                return self.reply(
                    200, {"data": [{"index": i, "embedding": [1.0, 1.0]} for i, _ in enumerate(body["input"])]}
                )
            return self.reply(
                200,
                {
                    "model": "protocol-fixture",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": values["answer"]},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
            )

        def reply(self, status, body):
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
