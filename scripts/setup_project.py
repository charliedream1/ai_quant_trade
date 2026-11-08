"""Bootstrap a reproducible project environment outside the repository tree."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any

logger: Any
try:
    from loguru import logger as _loguru_logger

    logger = _loguru_logger
except ImportError:  # The bootstrap may run before project dependencies are installed.

    class _BootstrapLogger:
        @staticmethod
        def info(message: str, *args: object) -> None:
            sys.stdout.write(message.format(*args) + "\n")

        @staticmethod
        def error(message: str, *args: object) -> None:
            sys.stderr.write(message.format(*args) + "\n")

    logger = _BootstrapLogger()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_FILES = {
    "base": ("requirements.txt",),
    "models": ("requirements.txt", "requirements-models.txt"),
    "llm": ("requirements.txt", "requirements-llm.txt"),
    "channels": ("requirements.txt", "egs/requirements/channels.txt"),
    "observability": ("requirements.txt", "egs/requirements/observability.txt"),
    "docs": ("requirements-docs.txt",),
    "development": ("requirements.txt", "requirements-models.txt", "egs/requirements/development.lock.txt"),
}


def default_runtime_root() -> Path:
    """Choose an E-drive runtime when it exists, with a portable fallback elsewhere."""
    configured = os.environ.get("AQT_RUNTIME_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == "nt" and Path("E:/").exists():
        return Path("E:/aqt-runtime/ai_quant_trade").resolve()
    return (Path.home() / ".cache" / "ai_quant_trade").resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager", choices=("pip", "uv"), default="uv")
    parser.add_argument("--profile", choices=tuple(PROFILE_FILES), default="base")
    parser.add_argument("--python", dest="python_executable", default=sys.executable)
    parser.add_argument("--runtime-root", type=Path, default=None)
    parser.add_argument("--environment", type=Path, default=None)
    parser.add_argument("--install-zvec", action="store_true", help="Install the locked zvec-grep npm package")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def run(command: list[str], *, cwd: Path, env: dict[str, str], dry_run: bool) -> None:
    logger.info("Running: {}", " ".join(command))
    if not dry_run:
        subprocess.run(command, cwd=cwd, env=env, check=True)  # nosec B603


def write_activation(runtime_root: Path, environment: Path, tools: Path, cache: Path, temp: Path) -> None:
    runtime_root.mkdir(parents=True, exist_ok=True)
    values = {
        "ALL_IN_ONE_WEB_ENVIRONMENT": str(environment),
        "ALL_IN_ONE_TOOLS_DIR": str(tools),
        "UV_CACHE_DIR": str(cache / "uv"),
        "PIP_CACHE_DIR": str(cache / "pip"),
        "TEMP": str(temp),
        "TMP": str(temp),
        "TMPDIR": str(temp),
    }
    (runtime_root / "runtime.env").write_text(
        "\n".join(f"{key}={json.dumps(value, ensure_ascii=False)}" for key, value in values.items()) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    # Single-quoted PowerShell literals prevent interpolation; double apostrophes preserve quotes.
    ps_lines = ["$env:" + key + " = '" + value.replace("'", "''") + "'" for key, value in values.items()]
    # Windows PowerShell 5.1 needs a BOM to read non-ASCII paths correctly.
    (runtime_root / "activate.ps1").write_text("\n".join(ps_lines) + "\n", encoding="utf-8-sig", newline="\n")
    sh_lines = [f"export {key}={shlex.quote(value)}" for key, value in values.items()]
    (runtime_root / "activate.sh").write_text("\n".join(sh_lines) + "\n", encoding="utf-8", newline="\n")


def install_python(args: argparse.Namespace, environment: Path, env: dict[str, str]) -> None:
    version_probe = subprocess.run(
        [args.python_executable, "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )  # nosec B603
    major, minor = (int(item) for item in version_probe.stdout.strip().split(".", 1))
    if (major, minor) < (3, 10) or (major, minor) >= (3, 15):
        raise RuntimeError("The selected Python interpreter must be between 3.10 and 3.14")
    environment.parent.mkdir(parents=True, exist_ok=True)
    python_path = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python_path.exists():
        if args.manager == "uv":
            run(
                ["uv", "venv", str(environment), "--python", args.python_executable],
                cwd=PROJECT_ROOT,
                env=env,
                dry_run=args.dry_run,
            )
        else:
            run(
                [args.python_executable, "-m", "venv", str(environment), "--without-pip"],
                cwd=PROJECT_ROOT,
                env=env,
                dry_run=args.dry_run,
            )
            run(
                [str(python_path), "-m", "ensurepip", "--upgrade", "--default-pip"],
                cwd=PROJECT_ROOT,
                env=env,
                dry_run=args.dry_run,
            )
    if args.dry_run:
        python_path.parent.mkdir(parents=True, exist_ok=True)
    if args.manager == "pip":
        run(
            [
                str(python_path),
                "-m",
                "pip",
                "install",
                "--upgrade",
                "pip==25.0.1",
                "setuptools==75.3.4",
                "wheel==0.45.1",
            ],
            cwd=PROJECT_ROOT,
            env=env,
            dry_run=args.dry_run,
        )
    for relative in PROFILE_FILES[args.profile]:
        if args.manager == "pip":
            command = [str(python_path), "-m", "pip", "install", "-r", str(PROJECT_ROOT / relative)]
        else:
            command = ["uv", "pip", "install", "--python", str(python_path), "-r", str(PROJECT_ROOT / relative)]
        run(command, cwd=PROJECT_ROOT, env=env, dry_run=args.dry_run)


def install_zvec(tools: Path, cache: Path, env: dict[str, str], dry_run: bool) -> None:
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm or not shutil.which("node"):
        raise RuntimeError("--install-zvec requires Node.js and npm on PATH")
    source = PROJECT_ROOT / "egs/requirements/zvec-grep"
    destination = tools / "zvec-grep"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(source / name, destination / name)
    run(
        [npm, "ci", "--prefix", str(destination), "--cache", str(cache / "npm"), "--no-fund", "--no-audit"],
        cwd=PROJECT_ROOT,
        env=env,
        dry_run=dry_run,
    )


def main() -> int:
    args = parse_args()
    runtime_root = (args.runtime_root or default_runtime_root()).resolve()
    environment = (args.environment or runtime_root / ".venv-secure").resolve()
    tools = (runtime_root / "tools").resolve()
    cache = (runtime_root / "cache").resolve()
    temp = (runtime_root / "tmp").resolve()
    for path in (tools, cache, temp):
        path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "ALL_IN_ONE_WEB_ENVIRONMENT": str(environment),
            "ALL_IN_ONE_TOOLS_DIR": str(tools),
            "UV_CACHE_DIR": str(cache / "uv"),
            "PIP_CACHE_DIR": str(cache / "pip"),
            "TEMP": str(temp),
            "TMP": str(temp),
            "TMPDIR": str(temp),
        }
    )
    if args.manager == "pip":
        env["PIP_INDEX_URL"] = os.environ.get("AQT_PYPI_INDEX_URL", "https://pypi.org/simple")
        env.pop("PIP_EXTRA_INDEX_URL", None)
    write_activation(runtime_root, environment, tools, cache, temp)
    install_python(args, environment, env)
    if args.install_zvec:
        install_zvec(tools, cache, env, args.dry_run)
    activation = runtime_root / ("activate.ps1" if os.name == "nt" else "activate.sh")
    logger.info("Bootstrap complete. Source {} before starting the service.", activation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
