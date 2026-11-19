"""Opt-in artifact acceptance; every probe runs outside the source checkout."""

import json
import os
import subprocess
from pathlib import Path

import pytest

PYTHON = os.environ.get("AIQUANT_TEST_INSTALLED_PYTHON")
pytestmark = pytest.mark.skipif(
    not PYTHON, reason="Set AIQUANT_TEST_INSTALLED_PYTHON to a disposable wheel environment"
)


def run(script, tmp_path):
    environment = {**os.environ, "ALL_IN_ONE_WORKSPACE": str(tmp_path / "workspace"), "PYTHONDONTWRITEBYTECODE": "1"}
    environment.pop("PYTHONPATH", None)
    if os.environ.get("AIQUANT_TEST_INSTALLED_TARGET"):
        environment["PYTHONPATH"] = os.environ["AIQUANT_TEST_INSTALLED_TARGET"]
    environment.pop("ALL_IN_ONE_DATA_DIR", None)
    environment.update(ALL_IN_ONE_DATA_MODE="mock", ALL_IN_ONE_HELP_DOCS_AUTO_BUILD="false")
    result = subprocess.run(
        [str(PYTHON), "-c", script],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return result


def test_installed_import_database_and_assets(tmp_path):
    run(
        """from pathlib import Path
import src
from src.core.paths import INSTALLED,PROJECT_ROOT,SOURCE_ROOT
from src.core.config import get_settings
from src.core.database import Database
assert INSTALLED
assert Path(src.__file__).resolve().is_relative_to(SOURCE_ROOT)
assert not PROJECT_ROOT.is_relative_to(SOURCE_ROOT)
assert get_settings().data_dir.is_relative_to(PROJECT_ROOT)
assert (SOURCE_ROOT/'src/core/database_schema.sql').is_file()
assert (SOURCE_ROOT/'src/frontend/assets/workspace_routes.js').is_file()
assert Database().query_one('SELECT 1 AS ready')['ready']==1
""",
        tmp_path,
    )


def test_installed_offline_cli_and_help(tmp_path):
    result = run(
        """import json,sys
from src.cli.catalog import commands
from src.core.paths import INSTALLED
assert INSTALLED and len(commands())>150
sys.stdout.write(json.dumps({'commands':len(commands())}))
""",
        tmp_path,
    )
    assert json.loads(result.stdout)["commands"] > 150
    environment = {**os.environ, "ALL_IN_ONE_WORKSPACE": str(tmp_path / "workspace")}
    environment.pop("PYTHONPATH", None)
    if os.environ.get("AIQUANT_TEST_INSTALLED_TARGET"):
        environment["PYTHONPATH"] = os.environ["AIQUANT_TEST_INSTALLED_TARGET"]
    for module in ("src", "src.cli"):
        result = subprocess.run(
            [str(PYTHON), "-m", module, "--help"],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
    scripts = Path(PYTHON).parent
    if os.environ.get("AIQUANT_TEST_INSTALLED_TARGET"):
        scripts = Path(os.environ["AIQUANT_TEST_INSTALLED_TARGET"]) / "bin"
    for command in ("aiquant", "aiquant-server"):
        executable = scripts / (command + (".exe" if os.name == "nt" else ""))
        assert executable.is_file()
        result = subprocess.run(
            [str(executable), "--help"],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        assert result.returncode == 0, result.stderr


def test_installed_api_and_strategy_worker(tmp_path):
    run(
        """from src.api.app import create_app
from fastapi.testclient import TestClient
from src.core.config import get_settings
from src.strategy.process_port import ProcessStrategyPort
from src.strategy.ports import StrategyContext
from src.core.repository import Repository
from src.knowledge.files import KnowledgeFiles
from src.knowledge.sag2_retrieval import SAG2Retrieval
with TestClient(create_app()) as client:
 assert client.get('/api/v1/health').status_code==200
 assert client.get('/api/v1/strategies').status_code==200
 assert client.get('/app/').status_code==200
 uploaded=client.post('/api/v1/kb/documents',data={'library_name':'package-acceptance'},files={'file':('risk.txt',b'Package risk control evidence. Portfolio drawdown controls are mandatory.','text/plain')})
 assert uploaded.status_code==200 and uploaded.json()['code']==0,uploaded.text
 listed=client.get('/api/v1/kb/documents',params={'library_name':'package-acceptance'}).json()
 assert listed['data']['items'],listed
 repo=Repository()
 docs=KnowledgeFiles(repo).documents('package-acceptance')
 rows,trace,status,metadata=SAG2Retrieval(repo).search('drawdown',docs,'bm25',5,1)
 assert rows and metadata['retrieval_backend']=='sag2'
source=get_settings().project_root/'egs/examples/strategy_examples/function_signal_strategy.py'
port=ProcessStrategyPort(source,{},'generate_signal')
port.close()
""",
        tmp_path,
    )


def test_installed_help_build(tmp_path):
    run(
        """from src.core.config import get_settings
from src.help_docs.builder import ensure_help_docs_site
settings=get_settings()
settings.help_docs_auto_build=True
status=ensure_help_docs_site(settings)
assert status.built and not status.fallback,status.message
assert (settings.help_docs_site_dir/'usage/knowledge/index.html').is_file()
""",
        tmp_path,
    )


def test_installed_code_can_remain_read_only(tmp_path):
    run(
        """import hashlib,stat
from pathlib import Path
import src
root=Path(src.__file__).parent
files=[p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
original={p:(p.stat().st_mode,hashlib.sha256(p.read_bytes()).hexdigest()) for p in files}
try:
 for p in files:p.chmod(stat.S_IREAD)
 from src.api.app import create_app
 from fastapi.testclient import TestClient
 with TestClient(create_app()) as client:
  assert client.get('/api/v1/health').status_code==200
  assert client.get('/app/').status_code==200
 assert all(hashlib.sha256(p.read_bytes()).hexdigest()==before[1] for p,before in original.items())
finally:
 for p,before in original.items():p.chmod(before[0])
""",
        tmp_path,
    )


def test_installed_strict_preflight_uses_distribution_metadata(tmp_path):
    if os.environ.get("AIQUANT_TEST_INSTALLED_TARGET"):
        pytest.skip("The shared Conda target intentionally permits existing dependency-version differences")
    run(
        """from src.core.runtime_environment import inspect_runtime
report=inspect_runtime(mode='strict')
assert report['passed'],report['errors']
assert len(report['declared'])>20
""",
        tmp_path,
    )
