"""SDK transport reuses the existing pinned requests destination policy."""

import httpx
import requests

from src.core.exceptions import BusinessError
from src.core.llm_config import llm_config
from src.core.network_policy import validate_url

from .model_budget import CallBudget


class ModelTransport(httpx.BaseTransport):
    def __init__(self, session: requests.Session, budget: CallBudget, base_url: str):
        self.session, self.budget = session, budget
        self.origin = httpx.URL(base_url)
        self.refusal: ValueError | BusinessError | None = None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        try:
            return self._handle_request(request)
        except (ValueError, BusinessError) as exc:
            self.refusal = exc
            raise

    def _handle_request(self, request: httpx.Request) -> httpx.Response:
        validate_url(str(request.url))
        if (request.url.scheme, request.url.host, request.url.port) != (
            self.origin.scheme,
            self.origin.host,
            self.origin.port,
        ):
            raise ValueError("模型请求不能转发到其他来源")
        remaining = self.budget.remaining()
        try:
            response = self.session.request(
                request.method,
                str(request.url),
                headers=dict(request.headers),
                data=request.read(),
                allow_redirects=False,
                timeout=(min(llm_config()["defaults"]["connect_seconds"], remaining), remaining),
            )
        except requests.Timeout as exc:
            raise httpx.ReadTimeout("模型请求超时", request=request) from exc
        except requests.RequestException as exc:
            raise httpx.ConnectError("模型连接失败", request=request) from exc
        self.budget.remaining()
        # requests has already decompressed content; avoid decoding it a second time.
        headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() not in {"content-encoding", "content-length", "transfer-encoding"}
        }
        try:
            return httpx.Response(response.status_code, headers=headers, content=response.content, request=request)
        finally:
            response.close()
