"""Local-first Skill entry point; stdout is machine-readable, logs use Loguru."""

import argparse
import json
import sys
from threading import Event
from time import monotonic

from loguru import logger

from src.agent.providers import provider_catalog

from .catalog import preview, read_request, settings
from .export import export_skills
from .remote import remote_command
from .service import LocalSkillService


def output(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")
    sys.stdout.flush()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="本地量化研究Skills，无需启动网页；运行占用当前进程")
    parser.add_argument(
        "command",
        choices=[
            "catalog",
            "providers",
            "preflight",
            "preview",
            "run",
            "show",
            "wait",
            "events",
            "cancel",
            "files",
            "export",
        ],
    )
    parser.add_argument("run_id", nargs="?")
    parser.add_argument("--config", help="项目内的Skill研究YAML")
    parser.add_argument("--host", choices=list(settings()["exports"]))
    parser.add_argument("--probe", action="store_true", help="只检查CLI安装/认证/协议，不生成模型内容")
    parser.add_argument("--format", choices=["json", "jsonl"], default="json")
    parser.add_argument("--base-url", help="显式使用远程平台；不设置时直接运行本地领域服务")
    args = parser.parse_args(argv)
    try:
        if args.base_url:
            value = remote_command(args, emit=output)
        else:
            value = local_command(args)
        output(value)
        return 1 if isinstance(value, dict) and value.get("status") in {"failed", "cancelled", "interrupted"} else 0
    except (Exception, KeyboardInterrupt) as exc:
        logger.error("Skill命令未完成：{}", exc)
        output({"status": "failed", "error": str(exc), "error_type": type(exc).__name__})
        return 1


def local_command(args):
    command = args.command
    if command == "catalog":
        return {"workflows": settings()["workflows"], "web_required": False}
    if command == "providers":
        return {"providers": provider_catalog(probe=args.probe)}
    if command == "export":
        if not args.host:
            raise ValueError("导出需要--host")
        return export_skills(args.host)
    if command in {"preview", "preflight", "run"}:
        if not args.config:
            raise ValueError("需要--config指定项目内研究YAML")
        payload = read_request(args.config)
        plan = preview(payload)
        if command != "run":
            return {**plan, **({"providers": provider_catalog(probe=args.probe)} if command == "preflight" else {})}
        callback = (lambda kind, data: output({"type": kind, "data": data})) if args.format == "jsonl" else None
        return LocalSkillService().run(payload, emit=callback)
    if not args.run_id:
        raise ValueError("需要运行ID")
    store = LocalSkillService().store
    if command == "events":
        return {"items": store.events(args.run_id)}
    if command == "files":
        return {"items": store.files(args.run_id)}
    if command == "cancel":
        return store.cancel(args.run_id)
    if command == "wait":
        started = monotonic()
        while store.get(args.run_id)["status"] in {"registered", "running"}:
            if monotonic() - started > settings()["limits"]["deadline_seconds"]:
                raise TimeoutError("等待已到时限；未自动重跑任务，请检查原进程和events")
            Event().wait(settings()["limits"]["poll_seconds"])
    return store.get(args.run_id)
