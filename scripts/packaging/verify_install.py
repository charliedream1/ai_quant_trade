"""CI artifact acceptance; subprocess paths are portable across Windows and Linux."""

import argparse
import os
import shutil

# Installer/interpreter invocations use fixed argv, never shell commands.
import subprocess  # nosec B404
import sys
from pathlib import Path


def execute(command, **kwargs):
    """Run explicitly selected build tools without shell interpretation."""
    return subprocess.run(command, check=True, **kwargs)  # nosec B603


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--artifacts", default=".pytest_tmp/distribution")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    temporary = output / "tmp"
    temporary.mkdir(exist_ok=True)
    os.environ.update(
        UV_CACHE_DIR=str(output / "uv-cache"),
        PIP_CACHE_DIR=str(output / "pip-cache"),
        PLAYWRIGHT_BROWSERS_PATH=str(output / "browsers"),
        TEMP=str(temporary),
        TMP=str(temporary),
        TMPDIR=str(temporary),
    )
    environment = output / "installed"
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("Install the documented uv version before running artifact acceptance")
    execute([uv, "venv", "--python", sys.executable, str(environment)])
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    wheel = next(Path(args.artifacts).glob("*.whl"))
    execute([uv, "pip", "install", "--python", str(python), str(wheel)])
    execute([uv, "pip", "check", "--python", str(python)])
    execute([uv, "pip", "install", "--python", str(python), "pytest==9.0.3", "playwright==1.59.0"])
    execute([str(python), "-m", "playwright", "install", "chromium"])
    process_env = {
        **os.environ,
        "AIQUANT_TEST_INSTALLED_PYTHON": str(python),
        "AIQUANT_TEST_DIST": str(Path(args.artifacts).resolve()),
    }
    process_env.pop("PYTHONPATH", None)
    execute(
        [str(python), "-m", "pytest", str(root / "tests/packaging"), "-q", "--basetemp", str(output / "tests")],
        cwd=root,
        env=process_env,
    )


if __name__ == "__main__":
    main()
