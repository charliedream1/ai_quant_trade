"""Bounded REST/SSE transport with no implicit mutation retries."""

import json
from contextlib import ExitStack
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import uuid4

import requests
from urllib3.exceptions import ReadTimeoutError

from .errors import CliError, ExitCode


class Client:
    def __init__(self, config: dict[str, Any], *, market: str | None = None) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.trust_env = False
        self.headers = {"X-Request-ID": uuid4().hex}
        if market:
            if market not in {"CN", "US"}:
                raise CliError("--market 必须为 CN 或 US")
            self.headers["X-AIQuant-Market"] = market
        if config.get("authorization"):
            self.headers["Authorization"] = str(config["authorization"])
        self.started = monotonic()

    def close(self) -> None:
        self.session.close()

    def _open(self, request: dict[str, Any], stack: ExitStack, *, long: bool = False, upload: str | None = None):
        timeouts = self.config["timeouts"]
        remaining = float(timeouts["deadline"]) - (monotonic() - self.started)
        if remaining <= 0:
            raise CliError("命令总时限已到", ExitCode.TIMEOUT, outcome="unknown")
        kwargs: dict[str, Any] = {
            "params": request["query"],
            "headers": self.headers,
            "timeout": (
                min(float(timeouts["connect"]), remaining),
                min(float(timeouts["long_read"] if long else timeouts["read"]), remaining),
            ),
            "stream": True,
            "allow_redirects": False,
        }
        if upload:
            path = Path(upload)
            try:
                stream = stack.enter_context(path.open("rb"))
            except OSError as exc:
                raise CliError("上传文件不存在或无法读取") from exc
            kwargs.update(
                files={"file": (path.name, stream)},
                data={
                    key: json.dumps(value) if isinstance(value, list | dict) else str(value)
                    for key, value in request["body"].items()
                },
            )
        elif request["method"] != "GET":
            kwargs["json"] = request["body"]
        url = str(self.config["base_url"]).rstrip("/") + str(self.config["api_prefix"]).rstrip("/") + request["path"]
        response = stack.enter_context(self.session.request(request["method"], url, **kwargs))
        if response.status_code >= 300:
            raise CliError(
                f"HTTP 请求失败：{response.status_code}", ExitCode.TRANSPORT, http_status=response.status_code
            )
        return response

    def _timeout(self, request: dict[str, Any], message: str) -> CliError:
        return CliError(
            message,
            ExitCode.TIMEOUT,
            outcome="unknown",
            mutation_may_have_completed=request["method"] != "GET",
            request_id=self.headers["X-Request-ID"],
        )

    def _response(self, response: Any, request: dict[str, Any]) -> dict[str, Any]:
        content = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            if monotonic() - self.started > self.config["timeouts"]["deadline"]:
                raise self._timeout(request, "超过命令总时限；未自动重试")
            content.extend(chunk)
            if len(content) > self.config["limits"]["response_bytes"]:
                raise CliError("响应超过大小上限", ExitCode.TRANSPORT)
        result = json.loads(content.decode("utf-8"))
        if not isinstance(result, dict) or not {"code", "message", "data"}.issubset(result):
            raise CliError("服务未返回业务信封", ExitCode.TRANSPORT)
        result["meta"] = {
            **(result.get("meta") or {}),
            "request_id": response.headers.get("X-Request-ID", self.headers["X-Request-ID"]),
            "context": self.config["context"],
            "elapsed_ms": round((monotonic() - self.started) * 1000),
            "client_version": "1",
        }
        return result

    def request(self, request: dict[str, Any], *, execution: bool = False, upload: str | None = None) -> dict[str, Any]:
        try:
            with ExitStack() as stack:
                response = self._open(request, stack, long=execution, upload=upload)
                return self._response(response, request)
        except requests.Timeout as exc:
            raise self._timeout(request, "请求超时；服务端可能仍在执行，未自动重试") from exc
        except requests.ConnectionError as exc:
            if any(isinstance(cause, ReadTimeoutError) for cause in exc.args):
                raise self._timeout(request, "响应读取超时；未自动重试") from exc
            raise CliError(
                "服务连接失败或响应中断",
                ExitCode.TRANSPORT,
                outcome="unknown",
                mutation_may_have_completed=request["method"] != "GET",
            ) from exc
        except (requests.RequestException, UnicodeError, ValueError) as exc:
            raise CliError("HTTP/JSON 响应格式无效", ExitCode.TRANSPORT) from exc

    def stream(self, request: dict[str, Any]):
        try:
            with ExitStack() as stack:
                response = self._open(request, stack, long=True)
                if "text/event-stream" not in response.headers.get("content-type", ""):
                    result = self._response(response, request)
                    yield {"type": "result", "data": result}
                    return
                total = 0
                # Batch strategy traces are large; interactive chat keeps byte-level first-token delivery.
                lines = (
                    response.iter_lines()
                    if request["path"].startswith("/strategy-pipeline-runs")
                    else response.iter_lines(chunk_size=1)
                )
                for line in lines:
                    total += len(line)
                    if total > self.config["limits"]["response_bytes"]:
                        raise CliError("事件流超过大小上限", ExitCode.TRANSPORT)
                    if monotonic() - self.started > self.config["timeouts"]["deadline"]:
                        raise self._timeout(request, "事件流超过总时限")
                    if line.startswith(b"data:"):
                        event = json.loads(line[5:].decode("utf-8"))
                        if not isinstance(event, dict) or "type" not in event or "data" not in event:
                            raise CliError("事件缺少类型或数据", ExitCode.TRANSPORT)
                        if event["type"] == "result" and (
                            not isinstance(event["data"], dict)
                            or not {"code", "message", "data"}.issubset(event["data"])
                        ):
                            raise CliError("最终事件缺少业务信封", ExitCode.TRANSPORT)
                        yield event
        except requests.Timeout as exc:
            raise self._timeout(request, "事件流中断；请查询已留档会话/报告，未重发消息") from exc
        except requests.ConnectionError as exc:
            if any(isinstance(cause, ReadTimeoutError) for cause in exc.args):
                raise self._timeout(request, "事件流读取超时；未重发消息") from exc
            raise CliError(
                "事件流连接失败或中断；未重发消息",
                ExitCode.TRANSPORT,
                outcome="unknown",
                request_id=self.headers["X-Request-ID"],
            ) from exc
        except (requests.RequestException, UnicodeError, ValueError) as exc:
            raise CliError("事件协议无效", ExitCode.TRANSPORT) from exc
