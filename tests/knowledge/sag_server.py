"""Real local HTTP contracts for SAG, ordinary model generation, embeddings and rerank."""

import copy
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4


@contextmanager
def sag_server(values):
    state = {"sources": {}, "requests": [], "fail": set(), "foreign": False, "pending": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            return

        def do_GET(self):  # noqa: N802
            source = self.path.split("/")[-2]
            self.reply(200, state["sources"].get(source, []))

        def do_POST(self):  # noqa: N802
            body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
            state["requests"].append((self.path, body))
            if self.path.endswith("/sources"):
                identifier = uuid4().hex
                state["sources"][identifier] = []
                self.reply(201, {"id": identifier})
            elif self.path.endswith("/ingest"):
                source = self.path.split("/")[-3]
                doc = {"id": uuid4().hex, "status": "pending" if state["pending"] else "ready", **body}
                state["sources"][source].append(doc)
                self.reply(201, doc)
            elif self.path.endswith("/search"):
                if body["strategy"] in state["fail"]:
                    self.reply(503, {"error": "controlled unavailable transport"})
                else:
                    sections = [
                        {
                            "source_id": source,
                            "chunk_id": document["id"],
                            "heading": document["title"],
                            "content": document["text"],
                            "score": 0.9,
                            "rank": 0,
                        }
                        for source in body["source_ids"]
                        for document in state["sources"][source]
                    ]
                    if state["foreign"] and sections:
                        sections[0]["source_id"] = "ungranted-source"
                    self.reply(
                        200, {"query": body["query"], "sections": sections, "summary": "unused upstream summary"}
                    )
            elif self.path.endswith("/rerank"):
                self.reply(
                    200,
                    {
                        "results": [
                            {"index": index, "relevance_score": 1 / (index + 1)}
                            for index in range(min(body["top_n"], len(body["documents"])))
                        ]
                    },
                )
            elif self.path.endswith("/embeddings"):
                self.reply(
                    200,
                    {
                        "data": [
                            {"index": index, "embedding": [1.0, 1.0 if "Alpha" in text else -1.0]}
                            for index, text in enumerate(body["input"])
                        ]
                    },
                )
            else:
                response = copy.deepcopy(values["model_completion"])
                prompt = body["messages"][-1]["content"]
                text = (
                    json.dumps({"keywords": values["keywords"], "sufficient": False})
                    if "keywords" in prompt
                    else values["answer"]
                )
                response["choices"][0]["message"]["content"] = text
                self.reply(200, response)

        def reply(self, status, value):
            encoded = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()
