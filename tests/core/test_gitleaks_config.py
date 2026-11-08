"""Exercise upload exclusions and secret detection using isolated Git repositories."""

import json
import secrets
import shutil
import string
import subprocess
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT_ROOT / ".gitleaks.toml"
COMMAND_TIMEOUT_SECONDS = 30
CANARY_BODY_LENGTH = 48
UPLOAD_CASES = [
    (".env", True),
    (".llm_env", True),
    (".migration-records/private.txt", True),
    (".workbuddy/memory/note.md", True),
    (".workbuddy/sessions/session.jsonl", True),
    (".codex/memory/note.md", True),
    (".codex/memories/notes.md", True),
    (".codex/sessions/session.jsonl", True),
    (".codex/auth.json", True),
    (".codex/state_5.sqlite", True),
    (".trae/memory/note.md", True),
    ("nested/.codex/sessions/session.jsonl", True),
    ("nested/.trae/memory/note.md", True),
    ("nested/.workbuddy/memory/note.md", True),
    ("docs/audit/run/result.json", True),
    ("docs/tasks.func.md", True),
    ("docs/tasks.spec.md", True),
    ("src/data/quotes.py", False),
    ("egs/config/platform/config.example.yaml", False),
    ("docs/usage/workspace.md", False),
    ("docs/usage/assets/demos/navigation.gif", False),
    (".agents/skills/quant-alpha-mining/SKILL.md", False),
    (".qoder/skills/quant-alpha-mining/SKILL.md", False),
    (".codebuddy/skills/quant-alpha-mining/SKILL.md", False),
    (".codex/skills/shared/SKILL.md", False),
    (".workbuddy/skills/shared/SKILL.md", False),
]
CANARY_PATHS = {
    ".env",
    ".llm_env",
    ".secrets",
    "src/core/credential_canary.py",
    "src/data/credential_canary.py",
    "uv.lock",
}


def _binary(name: str) -> str:
    executable = shutil.which(name)
    assert executable is not None, f"This security integration check requires {name} on PATH"
    return executable


def _run(command: list[str], directory: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=directory,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=COMMAND_TIMEOUT_SECONDS,
        check=False,
    )


@pytest.fixture()
def upload_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    result = _run([_binary("git"), "init", "--quiet"], repository)
    assert result.returncode == 0, result.stderr
    (repository / ".gitignore").write_text(
        (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8-sig"), encoding="utf-8"
    )
    return repository


def test_gitleaks_config_extends_default_rules() -> None:
    configuration = tomllib.loads(CONFIG.read_text(encoding="utf-8-sig"))
    assert configuration["extend"]["useDefault"] is True


@pytest.mark.parametrize(("relative_path", "ignored"), UPLOAD_CASES)
def test_git_upload_exclusions_preserve_public_sources(
    upload_repository: Path, relative_path: str, ignored: bool
) -> None:
    result = _run([_binary("git"), "check-ignore", "--no-index", "-q", relative_path], upload_repository)
    assert result.returncode in {0, 1}, result.stderr
    assert (result.returncode == 0) is ignored


@pytest.mark.parametrize("mode", ["directory", "staged"])
def test_credentials_in_source_lock_and_private_filenames_are_detected(
    upload_repository: Path, tmp_path: Path, mode: str
) -> None:
    # Random, never-issued values make a real detector exercise its full rules.
    alphabet = string.ascii_letters + string.digits
    token = "sk-" + "".join(secrets.choice(alphabet) for _ in range(CANARY_BODY_LENGTH))
    for relative in CANARY_PATHS:
        path = upload_repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'API_KEY = "{token}"\n', encoding="utf-8")
    if mode == "staged":
        result = _run([_binary("git"), "add", "--force", "--", *sorted(CANARY_PATHS)], upload_repository)
        assert result.returncode == 0, result.stderr
    report = tmp_path / f"{mode}-redacted.json"
    arguments = ["dir"] if mode == "directory" else ["git", "--pre-commit", "--staged"]
    result = _run(
        [
            _binary("gitleaks"),
            *arguments,
            str(upload_repository),
            "--config",
            str(CONFIG),
            "--gitleaks-ignore-path",
            str(upload_repository),
            "--ignore-gitleaks-allow",
            "--redact=100",
            "--no-banner",
            "--report-format",
            "json",
            "--report-path",
            str(report),
        ],
        upload_repository,
    )
    assert result.returncode == 1, result.stderr
    findings = json.loads(report.read_text(encoding="utf-8-sig"))
    files = [Path(item["File"]) for item in findings]
    detected = {
        path.relative_to(upload_repository).as_posix() if path.is_absolute() else path.as_posix() for path in files
    }
    assert detected == CANARY_PATHS
