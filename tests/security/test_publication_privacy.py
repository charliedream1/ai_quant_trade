"""Exercise packaging boundaries and load generated activation scripts with inert inputs."""

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pathspec
import pytest
import yaml
from dotenv import dotenv_values

from scripts.setup_project import write_activation

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_PATHS = [
    ".env",
    ".env.local",
    ".llm_env",
    ".secrets",
    ".codex/memories/notes.md",
    ".codex/sessions/session.jsonl",
    ".codex/auth.json",
    ".trae/memory/note.md",
    ".workbuddy/memory/note.md",
    "src/.codex/auth.json",
    "src/data/.workbuddy/memory/note.md",
    "egs/.env",
    "egs/config/platform/config.yaml",
    "docs/usage/.trae/session.json",
    "docs/tasks.spec.md",
    "docs/audit/private.json",
    "docs/usage/local.db",
    "unreviewed/private.txt",
]


def test_insight_storage_rejects_roots_outside_configured_boundaries(tmp_path: Path, monkeypatch) -> None:
    from src.engine.insights import store

    settings = SimpleNamespace(project_root=tmp_path / "checkout", data_dir=tmp_path / "configured-data")
    monkeypatch.setattr(store, "get_settings", lambda: settings)
    assert store.InsightStore().root.is_relative_to(settings.data_dir)
    with pytest.raises(ValueError):
        store.InsightStore(tmp_path / "unconfigured-sibling")


@pytest.mark.parametrize("relative", PRIVATE_PATHS)
def test_docker_context_excludes_private_inputs(relative: str) -> None:
    policy = pathspec.GitIgnoreSpec.from_lines((ROOT / ".dockerignore").read_text().splitlines())
    assert policy.match_file(relative), relative


@pytest.mark.parametrize(
    "relative",
    [
        "src/api/app.py",
        "src/data/eastmoney.py",
        "egs/config/knowledge/knowledge.yaml",
        "egs/requirements/zvec-grep/package-lock.json",
        "docs/usage/knowledge.md",
        "scripts/docs/docs_policy.py",
    ],
)
def test_docker_context_preserves_runtime_sources(relative: str) -> None:
    policy = pathspec.GitIgnoreSpec.from_lines((ROOT / ".dockerignore").read_text().splitlines())
    assert not policy.match_file(relative), relative


def test_dockerfile_has_no_whole_checkout_copy() -> None:
    for line in (ROOT / "Dockerfile").read_text().splitlines():
        if line.startswith("COPY ") and not line.startswith("COPY --from="):
            sources = shlex.split(line)[1:-1]
            assert sources and all(source not in {".", "./", "*"} for source in sources)


@pytest.mark.parametrize("configuration", ["mkdocs.yml", "mkdocs.platform.yml"])
def test_documentation_never_publishes_local_agent_state(configuration: str, tmp_path: Path) -> None:
    config = yaml.load((ROOT / configuration).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    rules = str(config["exclude_docs"])
    source = tmp_path / configuration / "docs"
    source.mkdir(parents=True)
    (source / "index.md").write_text("# Public guide\n\nPublication boundary check.\n", encoding="utf-8")
    marker = "PRIVATE-AGENT-MEMORY-CANARY"
    for name in (".codex", ".trae", ".workbuddy"):
        private = source / "nested" / name / "memory" / "private.md"
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_text(marker, encoding="utf-8")
        assert pathspec.GitIgnoreSpec.from_lines(rules.splitlines()).match_file(private.relative_to(source).as_posix())
    build_config = source.parent / "build.yml"
    build_config.write_text(
        yaml.safe_dump(
            {
                "site_name": "Publication boundary",
                "docs_dir": "docs",
                "site_dir": "site",
                "exclude_docs": rules,
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict", "-f", str(build_config)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    output = source.parent / "site"
    assert (output / "index.html").is_file()
    for path in output.rglob("*"):
        if path.is_file() and path.suffix in {".html", ".json"}:
            assert marker not in path.read_text(encoding="utf-8")


def _activation_values(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    runtime = tmp_path / "activation"
    # Expressions must stay literal. They throw only if quoting regresses; no files or secrets are touched.
    environment = Path(
        "runtime paths/\u8def\u5f84/$(throw 'must stay literal')/${AQT_UNSET}/apostrophe's/`tick`/\"quote\""
    )
    tools = Path("tools path/$HOME/$(false)/apostrophe's")
    cache, temporary = tmp_path / "cache path", tmp_path / "temporary path"
    write_activation(runtime, environment, tools, cache, temporary)
    return runtime, {
        "ALL_IN_ONE_WEB_ENVIRONMENT": str(environment),
        "ALL_IN_ONE_TOOLS_DIR": str(tools),
        "UV_CACHE_DIR": str(cache / "uv"),
        "PIP_CACHE_DIR": str(cache / "pip"),
        "TEMP": str(temporary),
        "TMP": str(temporary),
        "TMPDIR": str(temporary),
    }


def test_activation_metadata_roundtrips_without_interpolation(tmp_path: Path) -> None:
    runtime, values = _activation_values(tmp_path)
    assert dotenv_values(runtime / "runtime.env", interpolate=False) == values
    assert b"\r\n" not in (runtime / "activate.sh").read_bytes()


@pytest.mark.parametrize("shell", ["pwsh", "powershell"])
def test_powershell_activation_loads_paths_as_literals(tmp_path: Path, shell: str) -> None:
    executable = shutil.which(shell)
    if not executable:
        pytest.skip("PowerShell is not installed on this host")
    runtime, values = _activation_values(tmp_path)
    activation = str(runtime / "activate.ps1").replace("'", "''")
    rows = "; ".join(f"'{key}' = $env:{key}" for key in values)
    wrapper = tmp_path / "probe.ps1"
    wrapper.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)\n. '"
        + activation
        + "'\n@{"
        + rows
        + "} | ConvertTo-Json -Compress\n",
        encoding="utf-8-sig",
    )
    result = subprocess.run(
        [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(wrapper)],
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == values


def test_posix_activation_loads_paths_as_literals(tmp_path: Path) -> None:
    git = shutil.which("git")
    git_bash = Path(git).parent.parent / "bin" / "bash.exe" if git and os.name == "nt" else None
    executable = str(git_bash) if git_bash and git_bash.is_file() else shutil.which("bash")
    if not executable or (os.name == "nt" and "system32" in executable.lower()):
        pytest.skip("A local POSIX shell is not installed on this host")
    runtime, values = _activation_values(tmp_path)
    program = "import json, os, sys; sys.stdout.write(json.dumps({key: os.environ[key] for key in sys.argv[1:]}))"
    command = '. "$1"; "$2" -c "$3" "${@:4}"'
    environment = {**os.environ, "MSYS2_ENV_CONV_EXCL": "*"}
    result = subprocess.run(
        [
            executable,
            "--noprofile",
            "--norc",
            "-c",
            command,
            "privacy-probe",
            (runtime / "activate.sh").as_posix(),
            Path(sys.executable).as_posix(),
            program,
            *values,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
        env=environment,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == values
