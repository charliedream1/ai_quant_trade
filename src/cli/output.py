"""Pure machine results on stdout; diagnostic Loguru messages on stderr."""

import csv
import io
import json
import re
import sys
from typing import Any

from loguru import logger

from .config import project_output
from .errors import CliError

SENSITIVE = {"apikey", "authorization", "token", "password", "secret", "accesstoken", "refreshtoken"}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if re.sub(r"[-_]", "", str(key).lower()) in SENSITIVE else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        value = re.sub(r"(?i)(https?://)[^/\s:@]+:[^/\s@]+@", r"\1***@", value)
        value = re.sub(r"(?i)(\b(?:api[_-]?key|access[_-]?token|password|secret)\s*[=:]\s*)[^\s&,;]+", r"\1***", value)
        return re.sub(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/-]+=*", r"\1***", value)
    return value


def configure_output(verbose: bool = False, no_color: bool = False) -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    logger.remove()
    logger.add(sys.stdout, format="{message}", colorize=False, filter=lambda rec: rec["extra"].get("cli_result", False))
    logger.add(
        sys.stderr,
        format="{level} | {message}",
        colorize=not no_color and sys.stderr.isatty(),
        level="DEBUG" if verbose else "WARNING",
        filter=lambda rec: not rec["extra"].get("cli_result", False),
    )


def emit_text(text: str) -> None:
    logger.bind(cli_result=True).opt(raw=True).info("{}", text if text.endswith("\n") else text + "\n")


def json_text(value: Any) -> str:
    return json.dumps(redact(value), ensure_ascii=False, allow_nan=False)


def render(result: dict[str, Any], output_format: str, width: int) -> str:
    if output_format != "table":
        return json_text(result)
    data = redact(result.get("data"))
    rows = data.get("items", data) if isinstance(data, dict) else data
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        return json.dumps(redact(result), ensure_ascii=False, indent=2)
    keys = list(dict.fromkeys(key for row in rows for key in row))
    lines = [" | ".join(keys)]
    for row in rows:
        lines.append(" | ".join(str(row.get(key, ""))[:width].replace("\n", " ") for key in keys))
    lines.append(
        json_text(
            {
                "code": result.get("code"),
                "message": result.get("message"),
                "meta": result.get("meta"),
                "pagination": {
                    key: data[key] for key in ("page", "page_size", "total") if isinstance(data, dict) and key in data
                },
            }
        )
    )
    return "\n".join(lines)


def save_output(filename: str, text: str, overwrite: bool = False) -> str:
    path = project_output(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w" if overwrite else "x", encoding="utf-8", newline="") as stream:
            stream.write(text + ("" if text.endswith("\n") else "\n"))
    except OSError as exc:
        raise CliError("无法写入输出文件；覆盖已有文件需 --overwrite") from exc
    return str(path)


def csv_text(rows: list[dict[str, Any]]) -> str:
    stream = io.StringIO(newline="")
    keys = list(dict.fromkeys(key for row in rows for key in row))
    writer = csv.DictWriter(stream, fieldnames=keys)
    writer.writeheader()
    for row in rows:
        safe = {}
        for key, value in redact(row).items():
            text = json_text(value) if isinstance(value, dict | list) else value
            if isinstance(text, str) and text.lstrip().startswith(("=", "+", "-", "@")):
                text = "'" + text
            safe[key] = text
        writer.writerow(safe)
    return stream.getvalue()
