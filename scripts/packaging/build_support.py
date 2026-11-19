"""Allowlisted wheel resources and source archives, independent of Git availability."""

import json
from pathlib import Path

from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

from src.distribution_manifest import POLICY, ROOT, package_resources, public_resources, selected


class ResourceBuild(build_py):
    def run(self):
        super().run()
        if self.editable_mode:
            return
        destination = Path(self.build_lib) / "src"
        for path in package_resources():
            target = destination / path.relative_to(ROOT / "src")
            target.parent.mkdir(parents=True, exist_ok=True)
            self.copy_file(str(path), str(target))
        bundle = destination / POLICY["directory"]
        names = []
        for path in public_resources():
            relative = path.relative_to(ROOT)
            target = bundle / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            self.copy_file(str(path), str(target))
            names.append(relative.as_posix())
        (bundle / "manifest.json").write_text(
            json.dumps({"schema": POLICY["schema"], "files": names}), encoding="utf-8"
        )


class PublicSdist(sdist):
    def make_release_tree(self, base_dir, files):
        files = set(public_resources()) | set(package_resources())
        files.update(
            path for path in (ROOT / "src").rglob("*.py") if selected(path) and "typing_stubs" not in path.parts
        )
        files.update(
            (ROOT / "setup.py", ROOT / "scripts/packaging/__init__.py", ROOT / "scripts/packaging/build_support.py")
        )
        super().make_release_tree(base_dir, sorted(path.relative_to(ROOT).as_posix() for path in files))
