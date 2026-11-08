"""Download pinned viewer assets and optionally unpack Office only inside this project."""

import argparse
import base64
import hashlib
import json
import os
import subprocess  # nosec B404
import sys
import tarfile
import zipfile
from pathlib import Path

import requests
import yaml
from loguru import logger

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from src.core.config import PROJECT_ROOT  # noqa: E402
from src.core.tool_paths import runtime_path, tools_root  # noqa: E402


def local(name: str) -> Path:
    path = runtime_path(name)
    if not (path.is_relative_to(PROJECT_ROOT) or path.is_relative_to(tools_root())):
        raise ValueError("Runtime paths must stay inside the project or configured tools directory")
    return path


def fetch(spec: dict) -> Path:
    path = local(spec["target"])
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        with requests.get(spec["url"], stream=True, timeout=60) as response:
            response.raise_for_status()
            with path.open("wb") as stream:
                for chunk in response.iter_content(1024 * 1024):
                    stream.write(chunk)
    content = path.read_bytes()
    if spec.get("sha256") and hashlib.sha256(content).hexdigest() != spec["sha256"]:
        raise ValueError(f"Checksum mismatch: {path.name}; existing file preserved")
    if (
        spec.get("integrity")
        and "sha512-" + base64.b64encode(hashlib.sha512(content).digest()).decode() != spec["integrity"]
    ):
        raise ValueError(f"Integrity mismatch: {path.name}; existing file preserved")
    logger.info("Verified {} ({} bytes)", path.name, len(content))
    return path


def copy_zip(
    archive: Path, destination: Path, names: list[str] | None = None, prefixes: list[str] | None = None
) -> None:
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            if entry.is_dir() or (
                names is not None
                and entry.filename not in names
                and not any(entry.filename.startswith(prefix + "/") for prefix in prefixes or [])
            ):
                continue
            path = (destination / entry.filename).resolve()
            if not path.is_relative_to(destination.resolve()):
                raise ValueError("Invalid archive path")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bundle.read(entry))


def assets(config: dict) -> None:
    pdf = config["pdfjs"]
    copy_zip(fetch(config["downloads"]["pdfjs"]), local(pdf["destination"]), pdf["files"], pdf["directories"])
    markdown = config["markdown"]
    destination = local(markdown["destination"])
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fetch(config["downloads"]["markdown"])) as bundle:
        for name in markdown["files"]:
            stream = bundle.extractfile(name)
            if stream is None:
                raise ValueError("Missing pinned Markdown resource")
            (destination / Path(name).name).write_bytes(stream.read())
    for item in (pdf, markdown):
        (local(item["destination"]) / "provenance.json").write_text(
            json.dumps({"downloads": config["downloads"], "selected": item}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def office(config: dict) -> None:
    if os.name != "nt":
        raise ValueError("Windows portable extraction only; configure a project-local LibreOffice on Linux")
    destination = local(config["office_destination"])
    if (destination / "SourceDir/LibreOffice/program/soffice.com").is_file():
        logger.info("Existing portable Office retained: {}", destination)
        return
    tools = runtime_path(".tools/lessmsi")
    copy_zip(fetch(config["downloads"]["lessmsi"]), tools)
    source = fetch(config["downloads"]["libreoffice"])
    destination.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = str(runtime_path(".tools/tmp"))
    os.environ["TMP"] = os.environ["TEMP"]
    runtime_path(".tools/tmp").mkdir(parents=True, exist_ok=True)
    with (destination / "extraction.log").open("wb") as stream:
        subprocess.run(  # nosec B603
            [str(tools / "lessmsi.exe"), "x", str(source), str(destination) + "\\"],
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--office", action="store_true", help="Also unpack a project-local Windows LibreOffice")
    args = parser.parse_args()
    config = yaml.safe_load(local("egs/config/knowledge/file_preview_runtime.yaml").read_text(encoding="utf-8"))
    assets(config)
    if args.office:
        office(config)
    logger.info("File preview runtime is ready; no system or Conda packages changed")


if __name__ == "__main__":
    main()
