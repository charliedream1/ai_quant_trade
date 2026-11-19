"""Installed-code location and an explicit writable workspace, without parent env discovery."""

import hashlib
import json
import os
from pathlib import Path

import yaml
from filelock import FileLock

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_ROOT = SOURCE_ROOT / "src/_distribution"
INSTALLED = (BUNDLE_ROOT / "manifest.json").is_file()
RESOURCE_ROOT = BUNDLE_ROOT if INSTALLED else SOURCE_ROOT


def workspace_root():
    policy = yaml.safe_load((RESOURCE_ROOT / "egs/config/platform/distribution.yaml").read_text(encoding="utf-8"))
    selected = os.environ.get(policy["workspace_environment"])
    if not selected and not INSTALLED:
        return SOURCE_ROOT
    workspace = (
        Path(selected).expanduser().resolve() if selected else (Path.cwd() / policy["default_workspace"]).resolve()
    )
    if workspace.is_relative_to(SOURCE_ROOT) and INSTALLED:
        raise ValueError("Select a writable workspace outside the installed package directory")
    workspace.mkdir(parents=True, exist_ok=True)
    if INSTALLED:
        manifest = (BUNDLE_ROOT / "manifest.json").read_bytes()
        names = json.loads(manifest)["files"]
    else:
        # Source workspaces copy only the same public resource selection as a wheel.
        from src.distribution_manifest import public_resources

        names = [path.relative_to(SOURCE_ROOT).as_posix() for path in public_resources()]
        manifest = json.dumps(names).encode()
    signature = hashlib.sha256(manifest).hexdigest()
    marker = workspace / ".aiquant-resources.json"
    lock_path = workspace / ".aiquant-resources.lock"
    if not all(path.resolve().is_relative_to(workspace) for path in (marker, lock_path)):
        raise ValueError("Workspace initialization metadata resolves outside the selected directory")
    with FileLock(str(lock_path)):
        if marker.is_file() and marker.read_text(encoding="utf-8") == signature:
            return workspace
        for name in names:
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Invalid distribution resource path")
            target = workspace / relative
            if not target.resolve().is_relative_to(workspace):
                raise ValueError("Workspace resource resolves outside the selected directory")
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with target.open("xb") as stream:
                    stream.write((RESOURCE_ROOT / relative).read_bytes())
            except FileExistsError:
                pass
        marker.write_text(signature, encoding="utf-8")
    return workspace


PROJECT_ROOT = workspace_root()


def project_file(relative):
    """Resolve a logical project path without copying installed Python code."""
    path = Path(relative)
    if path.is_absolute():
        return path
    return (SOURCE_ROOT if path.parts and path.parts[0] == "src" else PROJECT_ROOT) / path


def relative_project_path(path):
    """Keep source-manifest identities stable across source and wheel installations."""
    resolved = Path(path).resolve()
    code = SOURCE_ROOT / "src"
    return resolved.relative_to(SOURCE_ROOT) if resolved.is_relative_to(code) else resolved.relative_to(PROJECT_ROOT)
