"""Check the current project interpreter without installing, deleting or starting services."""

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.runtime_environment import inspect_runtime  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="核对运行环境隔离、版本和包来源")
    parser.add_argument("--role", default="web")
    args = parser.parse_args()
    result = inspect_runtime(args.role)
    logger.info(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
