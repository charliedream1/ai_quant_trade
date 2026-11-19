"""Check or explicitly refresh the public resource inventory before reviewing a build."""

import argparse
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.distribution_manifest import POLICY, ROOT, selected  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the candidate inventory for manual review")
    args = parser.parse_args()
    names = {ROOT / name for name in POLICY["files"] if (ROOT / name).is_file() or name == POLICY["inventory"]}
    names.update(path for name in POLICY["roots"] for path in (ROOT / name).rglob("*") if selected(path))
    names.update(
        path
        for name in POLICY["asset_roots"]
        for path in (ROOT / name).rglob("*")
        if selected(path) and path.suffix != ".py"
    )
    target = ROOT / POLICY["inventory"]
    if not target.resolve().is_relative_to(ROOT):
        raise ValueError("Resource inventory resolves outside the source project")
    body = "# File format: UTF-8 distribution resource inventory; one reviewed relative path per line.\n"
    body += "\n".join(sorted(path.relative_to(ROOT).as_posix() for path in names)) + "\n"
    if args.write:
        target.write_text(body, encoding="utf-8")
        logger.info("Wrote {} resource paths; review this diff before building", len(names))
    elif not target.is_file() or target.read_text(encoding="utf-8") != body:
        raise SystemExit("Resource inventory differs; inspect new resources before using --write")
    else:
        logger.info("Explicit resource inventory matches the public resource selection")


if __name__ == "__main__":
    main()
