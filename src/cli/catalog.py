"""Load explicit command contracts from small YAML files grouped by domain."""

from functools import lru_cache
from typing import Any

import yaml

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

from .config import PROJECT_ROOT
from .errors import CliError

CATALOG_ROOT = PROJECT_ROOT / "egs" / "cli"


@lru_cache(maxsize=1)
def commands() -> dict[str, dict[str, Any]]:
    index = yaml.load((CATALOG_ROOT / "commands.yaml").read_text(encoding="utf-8-sig"), Loader=SafeLoader)
    result = {}
    for filename in index["files"]:
        path = (CATALOG_ROOT / filename).resolve()
        if not path.is_relative_to(CATALOG_ROOT.resolve()):
            raise CliError("命令配置路径越界")
        payload = yaml.load(path.read_text(encoding="utf-8-sig"), Loader=SafeLoader)
        for name, value in payload["commands"].items():
            if name in result:
                raise CliError(f"命令重复：{name}")
            result[name] = value
    return result
