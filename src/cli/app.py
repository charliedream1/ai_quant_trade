"""Application entry: declarative commands, one HTTP policy, explicit outcomes."""

import sys
from pathlib import Path
from typing import Any

from .catalog import commands
from .client import Client
from .config import load_config, project_output
from .errors import CliError, ExitCode, result_exit
from .input import build_request
from .operations import collect, compose, real_evidence, request_data
from .output import configure_output, csv_text, emit_text, json_text, render, save_output
from .parser import HelpExitError, parse
from .policy import check_policy, operation_target, resolve_operation


def _generic(args: Any, request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    method = str(request["body"].pop("method", "GET")).upper()
    path = str(request["body"].pop("path", ""))
    operation = str(request["body"].pop("operation", ""))
    if operation:
        if operation not in commands():
            raise CliError("operation 必须为 api operations 中的完整命令名")
        definition = commands()[operation]
        path = definition.get("path", "")
        method = definition.get("method", "GET")
        if "{" in path:
            raise CliError("带资源 ID 的通用调用请指定 --method 和具体 --path")
    _, definition = resolve_operation(method, path)
    query_names = set(definition.get("query", {}))
    body = request["body"]
    unknown = set(body) - query_names - set(definition.get("fields", {}))
    if unknown:
        raise CliError("API 字段不在契约中：" + ", ".join(sorted(unknown)))
    if set(body).intersection(definition.get("unsupported_query", [])):
        raise CliError("当前后端尚未实现该筛选条件，不能静默忽略")
    return definition, {
        "method": method,
        "path": path,
        "body": {key: value for key, value in body.items() if key not in query_names},
        "query": {key: value for key, value in body.items() if key in query_names},
        "confirm_id": operation_target(definition, path, body),
    }


def execute(options: Any, args: Any, definition: dict[str, Any], config: dict[str, Any]) -> tuple[dict[str, Any], int]:
    special = definition.get("special")
    if special in {"operations", "describe"}:
        if special == "describe" and args.operation not in commands():
            raise CliError("命令不存在")
        data = (
            [{"command": name, **value} for name, value in commands().items()]
            if special == "operations"
            else commands()[args.operation]
        )
        return {"code": 0, "message": "离线命令契约；具体服务可用性请用 system capabilities", "data": data}, ExitCode.OK
    if special == "serve":
        from start import main as serve

        serve(
            [
                item
                for key in ("host", "port", "log_level")
                if hasattr(args, key)
                for item in ("--" + key.replace("_", "-"), str(getattr(args, key)))
            ]
        )
        return {"code": 0, "message": "服务已停止", "data": None}, ExitCode.OK
    request = build_request(options, args, definition, config["limits"]["input_bytes"])
    if special == "api":
        definition, request = _generic(args, request)
    check_policy(definition, request, options, config)
    if options.dry_run:
        return {"code": 0, "message": "本地请求预览；未发送", "data": request}, ExitCode.OK
    client = Client(config, market=options.market)
    try:
        return _run(client, request, definition, args, options, special)
    finally:
        client.close()


def _run(
    client: Client, request: dict[str, Any], definition: dict[str, Any], args: Any, options: Any, special: str | None
) -> tuple[dict[str, Any], int]:
    if options.attachment:
        if args._command_name != "ai ask":
            raise CliError("--attachment 仅用于 ai ask")
        identifiers = []
        for filename in options.attachment:
            upload = client.request(
                {"method": "POST", "path": "/ai-workspace/attachments", "query": {}, "body": {}}, upload=filename
            )
            if upload["code"] != 0:
                return upload, int(result_exit(upload))
            identifiers.append(upload["data"]["attachment_id"])
        request["body"]["attachments"] = identifiers
    if (
        options.require_real
        and definition.get("execution")
        and request["path"].split("/")[1]
        in {
            "backtests",
            "market",
            "stocks",
            "factors",
            "recommend-tasks",
            "etf",
        }
    ):
        capability = request_data(client, "/system/capabilities")
        if capability["code"] != 0 or (capability["data"] or {}).get("is_mock"):
            raise CliError("当前服务数据源为模拟或无法确认真实来源", ExitCode.CONDITION)
    emit_progress = options.stream or options.format == "jsonl"
    if definition.get("stream_path") and (emit_progress or definition.get("await_terminal")):
        stream_identifiers = {
            field[1:-1]: value
            for field, value in zip(definition["path"].split("/"), request["path"].split("/"), strict=True)
            if field.startswith("{")
        }
        request["path"] = definition["stream_path"].format(**stream_identifiers)
        final = None
        for event in client.stream(request):
            if event.get("type") == "result":
                final = event["data"]
                exit_code = _result_code(final, definition, options)
                final.setdefault("meta", {}).update(
                    exit_code=exit_code, context=client.config["context"], streamed=emit_progress
                )
                if emit_progress and options.output and exit_code == 0:
                    final["meta"]["artifact_path"] = save_output(
                        options.output, json_text(final), bool(options.overwrite)
                    )
            if emit_progress:
                emit_text(json_text(event))
        if final is None:
            raise CliError("事件流未返回最终结果；请查询会话/报告", ExitCode.TRANSPORT)
        return final, _result_code(final, definition, options)
    if options.stream:
        raise CliError("当前命令无真实事件流，请使用同步结果")
    if special == "export":
        if options.kind and options.kind != "trades":
            raise CliError("当前 CSV 导出只支持 --kind trades；指标/曲线请使用对应命令 --output 保存 JSON")
        options.all = True
    result = (
        compose(client, args, options)
        if special in {"snapshot", "compare"}
        else collect(client, request, definition, options)
    )
    return result, _result_code(result, definition, options)


def _result_code(result: dict[str, Any], definition: dict[str, Any], options: Any) -> int:
    exit_code = result_exit(
        result, execution=definition.get("execution", False), fail_on_verdict=options.fail_on_verdict or ""
    )
    if options.require_real and exit_code == 0:
        found, mocked = real_evidence(result.get("data"))
        if mocked or not found:
            result["message"] = "真实来源条件未满足或缺少来源证据"
            exit_code = ExitCode.CONDITION
    return int(exit_code)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    configure_output("--verbose" in arguments, "--no-color" in arguments)
    options = None
    try:
        options, args, definition = parse(arguments)
        config = load_config(options)
        options.format = config["format"]
        if options.output and project_output(options.output).exists() and not options.overwrite:
            raise CliError("输出文件已存在，请明确使用 --overwrite")
        result, exit_code = execute(options, args, definition, config)
        result.setdefault("meta", {}).update(exit_code=exit_code, context=config["context"])
        output_format = config["format"]
        if output_format == "auto":
            output_format = "table" if sys.stdout.isatty() else "json"
        if output_format not in {"table", "json", "jsonl"}:
            raise CliError("format 必须为 auto/table/json/jsonl")
        if options.output and exit_code == 0 and not result["meta"].get("streamed"):
            text = (
                csv_text(result["data"].get("items", []))
                if definition.get("special") == "export" and Path(options.output).suffix.lower() == ".csv"
                else render(result, "json", config["limits"]["table_width"])
            )
            result["meta"]["artifact_path"] = save_output(options.output, text, bool(options.overwrite))
        # A streaming command already emitted its terminal event.
        if not result["meta"].get("streamed"):
            emit_text(render(result, output_format, config["limits"]["table_width"]))
        return int(exit_code)
    except HelpExitError:
        return ExitCode.OK
    except KeyboardInterrupt:
        emit_text(
            json_text(
                {
                    "code": None,
                    "message": "等待已中断；服务器可能继续执行",
                    "data": None,
                    "meta": {"exit_code": int(ExitCode.INTERRUPTED), "outcome": "unknown"},
                }
            )
        )
        return ExitCode.INTERRUPTED
    except (CliError, OSError, ValueError, TypeError) as exc:
        error = exc if isinstance(exc, CliError) else CliError(str(exc))
        result = {**error.envelope, "meta": {**error.meta, "exit_code": error.exit_code}}
        emit_text(json_text(result))
        return error.exit_code
