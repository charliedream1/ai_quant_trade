"""Allowlisted wheel resources and source archives, independent of Git availability."""

import fnmatch
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "src/_distribution/manifest.json").is_file():
    ROOT = ROOT / "src/_distribution"
POLICY = yaml.safe_load((ROOT / "egs/config/platform/distribution.yaml").read_text(encoding="utf-8"))


def selected(path):
    relative = path.relative_to(ROOT).as_posix()
    return (
        path.is_file()
        and not path.is_symlink()
        and path.resolve().is_relative_to(ROOT)
        and not any(fnmatch.fnmatch(relative, pattern) for pattern in POLICY["exclude"])
        and (path.suffix.lower() in POLICY["extensions"] or path.name.upper().startswith(("LICENSE", "NOTICE")))
    )


def public_resources():
    return [path for path in inventory() if path.parts[len(ROOT.parts)] != "src"]


def package_resources():
    return [path for path in inventory() if path.parts[len(ROOT.parts)] == "src"]


def inventory():
    names = (ROOT / POLICY["inventory"]).read_text(encoding="utf-8").splitlines()
    paths = []
    for name in names:
        if not name or name.startswith("#"):
            continue
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT) or not selected(path):
            raise ValueError("Invalid or missing distribution resource: " + name)
        paths.append(path)
    return sorted(set(paths))
