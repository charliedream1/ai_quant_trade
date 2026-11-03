"""Offline argparse command tree driven by the explicit operation catalog."""

import argparse
from typing import Any, NoReturn

from .catalog import commands
from .errors import CliError
from .output import emit_text


class HelpExitError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["allow_abbrev"] = False
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> NoReturn:
        raise CliError(message)

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        if status:
            raise CliError(message or "参数格式无效")
        raise HelpExitError()

    def _print_message(self, message: str, file: Any = None) -> None:
        if message:
            emit_text(message)


def global_parser() -> Parser:
    parser = Parser(add_help=False, argument_default=argparse.SUPPRESS)
    for name in (
        "context",
        "base-url",
        "api-prefix",
        "config",
        "output",
        "file",
        "params-file",
        "confirm-id",
        "code-file",
        "message-file",
        "question-file",
        "format",
        "market",
        "fail-on-verdict",
        "ids",
        "kind",
    ):
        parser.add_argument("--" + name)
    for name in ("connect-timeout", "read-timeout", "deadline"):
        parser.add_argument("--" + name, type=float)
    for name in ("max-items", "session-id"):
        parser.add_argument("--" + name, type=int)
    for name in ("verbose", "quiet", "no-color", "all", "dry-run", "yes", "overwrite", "require-real", "stream"):
        parser.add_argument("--" + name, action="store_true")
    parser.add_argument("--set", action="append", dest="sets")
    parser.add_argument("--attachment", action="append")
    return parser


def parse(argv: list[str]) -> tuple[argparse.Namespace, argparse.Namespace, dict[str, Any]]:
    global_options, rest = global_parser().parse_known_args(argv)
    defaults = {action.dest: None for action in global_parser()._actions if action.dest != "help"}
    defaults.update(vars(global_options))
    global_options = argparse.Namespace(**defaults)
    root = Parser(
        prog="aiquant",
        description="AIQuant REST 客户端；支持 YAML 请求、--set 和 --format json/jsonl。全局选项可放在子命令前后。",
    )
    root.epilog = global_parser().format_help()
    parsers: dict[tuple[str, ...], Parser] = {(): root}
    subs: dict[tuple[str, ...], Any] = {}
    for name, definition in commands().items():
        words = tuple(name.split())
        for length, word in enumerate(words, 1):
            parent = words[: length - 1]
            if parent and rest[: len(parent)] != list(parent):
                break
            if parent not in subs:
                subs[parent] = parsers[parent].add_subparsers(dest=f"domain_{length}", required=True)
            if words[:length] not in parsers:
                parsers[words[:length]] = subs[parent].add_parser(word)
        if words not in parsers:
            continue
        leaf = parsers[words]
        leaf.set_defaults(_command_name=name)
        if rest[: len(words)] != list(words):
            continue
        for key, kind in definition.get("positions", {}).items():
            leaf.add_argument(key, type=int if kind == "int" else str)
        fields = {**definition.get("fields", {}), **definition.get("query", {})}
        for key in fields:
            if key in {"base_url", "config", "market"}:
                alias = {"base_url": "model-base-url", "config": "request-config", "market": "qlib-market"}[key]
                leaf.add_argument("--" + alias, dest=key, default=argparse.SUPPRESS)
                continue
            if key in defaults or key in definition.get("positions", {}):
                continue
            leaf.add_argument("--" + key.replace("_", "-"), default=argparse.SUPPRESS)
        leaf.epilog = "复杂请求支持 --file YAML/JSON、--params-file、--set 字段=值；--dry-run 不发送请求。"
    values = root.parse_args(rest)
    return global_options, values, commands()[values._command_name]
