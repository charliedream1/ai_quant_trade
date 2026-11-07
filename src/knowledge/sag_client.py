"""Bounded REST access to an explicitly configured self-hosted SAG service."""

import hashlib
import json
import time
from urllib.parse import quote, urlsplit

import requests

from src.core.env_file import resolve_env_value
from src.core.network_policy import network_session, validate_url

from .config import knowledge_config
from .tracing import traced


class RetrievalUnavailableError(Exception):
    """Expose a safe category without provider payloads or credentials."""


def sag_policy() -> dict:
    cfg = dict(knowledge_config()["sag"])
    cfg["enabled"] = (resolve_env_value(cfg["enabled_env"]) or str(cfg["enabled"])).lower() in {"1", "true", "yes"}
    cfg["base_url"] = (resolve_env_value(cfg["base_url_env"]) or cfg["base_url"]).rstrip("/")
    cfg["jev_enabled"] = resolve_env_value(cfg["jev_enabled_env"]).lower() in {"1", "true", "yes"}
    return cfg


class JsonConnection:
    def __init__(self, base_url: str, token: str, timeout: float, maximum: int, *, session=None):
        parsed, _ = validate_url(base_url)
        if parsed.query or parsed.fragment:
            raise ValueError("Service URL must not contain query parameters or fragments")
        self.base, self.token, self.timeout, self.maximum = base_url.rstrip("/"), token, timeout, maximum
        self.session = session or network_session()

    def close(self):
        self.session.close()

    def call(self, method, path, body=None):
        headers = {"Authorization": "Bearer " + self.token} if self.token else {}
        try:
            with self.session.request(
                method,
                self.base + path,
                json=body,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=False,
                stream=True,
            ) as response:
                if not 200 <= response.status_code < 300:
                    raise RetrievalUnavailableError("http_" + str(response.status_code))
                content = bytearray()
                for chunk in response.iter_content(65536):
                    content.extend(chunk)
                    if len(content) > self.maximum:
                        raise RetrievalUnavailableError("response_too_large")
                return json.loads(content.decode("utf-8"))
        except (requests.RequestException, UnicodeError, ValueError):
            raise RetrievalUnavailableError("connection_or_response_invalid") from None


class SAGClient:
    def __init__(self, *, policy=None, session=None):
        self.policy = policy or sag_policy()
        self.started = time.monotonic()
        base = self.policy["base_url"]
        if not urlsplit(base).path.rstrip("/").endswith("/api/v1"):
            base += "/api/v1"
        self.connection = JsonConnection(
            base,
            resolve_env_value(self.policy["token_env"]),
            self.policy["timeout_seconds"],
            self.policy["max_response_bytes"],
            session=session,
        )

    @property
    def identity(self):
        return hashlib.sha256(self.connection.base.encode()).hexdigest()

    def close(self):
        self.connection.close()

    def call(self, method, path, body=None):
        if not self.policy["enabled"]:
            raise RetrievalUnavailableError("sag_disabled")
        remaining = self.policy["deadline_seconds"] - (time.monotonic() - self.started)
        if remaining <= 0:
            raise RetrievalUnavailableError("sag_deadline")
        self.connection.timeout = min(remaining, self.policy["timeout_seconds"])
        return self.connection.call(method, path, body)

    def create_source(self, name):
        return self.call("POST", "/sources", {"name": name, "connector_kind": "file_upload", "config": {}})

    def ingest(self, source_id, title, text):
        return self.call(
            "POST", "/sources/" + quote(source_id, safe="") + "/documents/ingest", {"title": title, "text": text}
        )

    def documents(self, source_id):
        return self.call("GET", "/sources/" + quote(source_id, safe="") + "/documents")

    @traced("tool.sag_search", "tool")
    def search(self, query, sources, strategy, limit):
        if not sources or len(sources) > self.policy["max_sources"]:
            raise RetrievalUnavailableError("sag_source_scope_invalid")
        if strategy not in {"multi_jev", "multi", "vector", "multi_es_fast"}:
            raise ValueError("Unknown SAG retrieval strategy")
        return self.call(
            "POST",
            "/search",
            {
                "query": query,
                "source_ids": sources,
                "strategy": strategy,
                "top_k": limit,
                "save_exploration": False,
                "include_ranked_candidates": False,
            },
        )
