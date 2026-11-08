"""Client-only YAML configuration; no application settings or database imports."""

import os
from math import isfinite
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from dotenv import dotenv_values

from .errors import CliError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "egs/config/platform/cli.yaml"
EXAMPLE_PATH = PROJECT_ROOT / "egs" / "config" / "platform" / "cli.example.yaml"


def load_config(options: Any) -> dict[str, Any]:
    env = {**dotenv_values(PROJECT_ROOT / ".env"), **os.environ}
    path = Path(
        options.config or env.get("ALL_IN_ONE_CLI_CONFIG") or (CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_PATH)
    )
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
        name = options.context or env.get("ALL_IN_ONE_CLI_CONTEXT") or payload["default_context"]
        context = dict(payload["contexts"][name])
        limits = dict(payload["limits"])
        timeouts = dict(payload["timeouts"])
    except (OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        raise CliError("CLI 配置不存在或格式无效") from exc
    context["base_url"] = options.base_url or env.get("ALL_IN_ONE_CLI_BASE_URL") or context["base_url"]
    context["api_prefix"] = options.api_prefix or env.get("ALL_IN_ONE_CLI_API_PREFIX") or context["api_prefix"]
    parsed = urlsplit(str(context["base_url"]))
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise CliError("base-url 必须为不含凭证或查询参数的 HTTP(S) 地址")
    prefix = str(context["api_prefix"])
    if not prefix.startswith("/") or ".." in prefix or "?" in prefix or "#" in prefix:
        raise CliError("api-prefix 格式无效")
    for attr, key in (("connect_timeout", "connect"), ("read_timeout", "read"), ("deadline", "deadline")):
        if getattr(options, attr, None) is not None:
            timeouts[key] = getattr(options, attr)
    if options.read_timeout is not None:
        timeouts["long_read"] = options.read_timeout
    if any(not isfinite(float(value)) or float(value) <= 0 for value in timeouts.values()):
        raise CliError("超时必须为正数")
    if not isinstance(context.get("allow_live_actions"), bool):
        raise CliError("allow_live_actions 必须为 YAML 布尔值")
    auth = env.get(str(context.get("authorization_env") or ""))
    output_format = options.format or payload["output"]
    if output_format not in {"auto", "table", "json", "jsonl"}:
        raise CliError("format 必须为 auto/table/json/jsonl")
    if any(int(value) <= 0 for value in limits.values()):
        raise CliError("配置大小和数量上限必须为正数")
    return {
        **context,
        "context": name,
        "timeouts": timeouts,
        "limits": limits,
        "format": output_format,
        "authorization": auth,
    }


def project_output(value: str) -> Path:
    path = Path(value).resolve()
    if not path.is_relative_to(PROJECT_ROOT.resolve()):
        raise CliError("输出路径必须位于当前项目内")
    return path
