"""Bounded JSON transport for optional evidence-scoring providers."""

import json

import requests

from src.core.network_policy import network_session, validate_url


class RetrievalUnavailableError(Exception):
    """Expose safe provider failure categories without credentials or payloads."""


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
