"""Explicit remote mode reuses the established REST client and its deadlines."""

from threading import Event
from time import monotonic
from types import SimpleNamespace

from src.cli.client import Client
from src.cli.config import load_config

from .catalog import read_request, settings


def remote_command(args, emit=None):
    if args.command == "export":
        raise ValueError("Skill导出只允许在本项目本地执行")
    options = SimpleNamespace(
        config=None,
        context=None,
        base_url=args.base_url,
        api_prefix=None,
        connect_timeout=None,
        read_timeout=None,
        deadline=None,
        format=args.format,
    )
    config = load_config(options)
    client = Client(config)

    def request(method, path, body=None, query=None):
        envelope = client.request(
            {"method": method, "path": path, "body": body or {}, "query": query or {}}, execution=method == "POST"
        )
        if envelope["code"] != 0:
            raise ValueError(envelope["message"])
        return envelope["data"]

    try:
        command = args.command
        if command == "catalog":
            return request("GET", "/research-skills")
        if command == "providers":
            return request("GET", "/agent-providers", query={"probe": str(args.probe).lower()})
        if command in {"preview", "preflight", "run"}:
            if not args.config:
                raise ValueError("需要--config指定研究YAML")
            payload = read_request(args.config)
            if payload.get("imports"):
                raise ValueError("远程模式请先通过平台数据导入接口上传文件，再使用已有数据集ID")
            path = "/research-skills/runs" if command == "run" else "/research-skills/preview"
            value = request("POST", path, payload)
            if command != "run":
                return value
            run_id = value["run_id"]
        else:
            run_id = args.run_id
        if not run_id:
            raise ValueError("需要运行ID")
        base = "/research-skills/runs/" + run_id
        if command in {"events", "files"}:
            return request("GET", base + "/" + command)
        if command == "cancel":
            return request("POST", base + "/cancel")
        cursor, started = 0, monotonic()
        while True:
            value = request("GET", base)
            if args.format == "jsonl" and emit:
                events = request("GET", base + "/events")["items"]
                for event in events[cursor:]:
                    emit(event)
                cursor = len(events)
            if command == "show" or value["status"] not in {"registered", "running"}:
                return value
            if monotonic() - started > config["timeouts"]["deadline"]:
                raise TimeoutError("等待远程任务超时；未自动重跑，可按运行ID继续查询")
            Event().wait(settings()["limits"]["poll_seconds"])
    finally:
        client.close()
