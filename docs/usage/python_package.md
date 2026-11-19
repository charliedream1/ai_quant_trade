# Install AIQuant as a Python distribution

The distribution name is **b001-all-in-one**, its existing Python import namespace
is **src**, and its commands are **aiquant** and **aiquant-server**. Installing the
distribution supplies application code, public configuration, SQL migrations,
frontend assets, skills, examples and the built-in help sources. Do not copy only
the Python files or add a checkout to `PYTHONPATH` to simulate an installation.

## Installation

Use a dedicated venv or Conda environment with a supported interpreter. The base
Python range is 3.10.1–3.14; optional workers and third-party tools retain their own
version and platform limits. The distribution does not support Python 3.9/3.15,
arbitrary operating systems or every accelerator configuration.

Build from the repository with `uv build --out-dir <artifact-directory>`. This
produces a wheel and source archive. Install the wheel using either
`python -m pip install <wheel-path>` or
`uv pip install --python <environment-python> <wheel-path>`. Both installers also
accept the source archive and `-e .` for editable development installation.
`python -m pip install .` and `uv sync --locked` install the project directly.
Existing `python -m pip install -r requirements.txt` remains a source-development
dependency installation; follow it with `python -m pip install --no-deps -e .` if
installed console commands are needed. Base dependencies retain exact tested pins.

Select extras deliberately: `llm`, `models`, `tdx`, `observability`, `channels` and
`dev`. For example, request `b001-all-in-one[observability]` when installing a
published/local named distribution. `llm` and `tdx` must stay in separate
environments because their HTTPX constraints conflict. Qlib and image decoding
use separate worker profiles; installing a base wheel does not install those
environments, GPU drivers, Node.js, ripgrep, LibreOffice or model CLIs.

## Workspace and startup

Launch `aiquant-server --workspace <workspace-directory>` or
`python -m src --workspace <workspace-directory>`. CLI serving is also available
through `aiquant system serve`; set `ALL_IN_ONE_WORKSPACE` before invoking the CLI
when selecting a workspace through that route. `--host`, `--port`, `--log-level`
and `--reload` retain the source launcher's meanings.

An installed application defaults to `.aiquant` inside the launch directory when
no workspace is selected. Use an explicit directory or `ALL_IN_ONE_WORKSPACE` for
stable state across launch directories. Package code stays in the installation;
configuration, `.env`, data, logs, uploads and outputs belong to the workspace.
Relative storage paths resolve against this workspace, not `site-packages` or an
unrelated current directory. Create local overrides under
`egs/config/platform/config.yaml` and credentials in the workspace's local `.env`.

Initialization copies only listed public resources and never overwrites existing
files or imports a checkout's private configuration/memory. Restarts preserve
overrides and databases. New releases add missing public defaults; existing
overrides are retained for deliberate review. Keep the workspace outside the
installed package directory. Treat it as private, including `.env` and generated
tool/agent state. Changing `ALL_IN_ONE_WORKSPACE` after importing application
modules is unsupported; select it before starting a new process.

The source checkout still supports `python start.py` and PyCharm debugging.
Without a workspace selection, source/editable execution uses the checkout as
before. An explicit workspace also works with a source checkout. Non-strict mode
is the default: tested-version or environment-location differences are warnings,
while missing required dependencies and unsupported Python versions stop startup.
Strict mode is opt-in with `ALL_IN_ONE_RUNTIME_MODE=strict`; an installed wheel
checks its own dependency metadata and current environment. Use explicit role
environment settings when a particular interpreter location must be enforced.

## External tools and development

Configure `ALL_IN_ONE_TOOLS_DIR` to keep tools outside an installation. Public tool
setup entry points are copied into `egs/entrypoints/` in the workspace. Follow
[installation](installation.md) and [CLI setup](cli_installation.md) for their
prerequisites; credentials and account login are never supplied by the wheel.
Do not merge the Qlib/image package sets into the base web environment.

Build resources are listed in `egs/config/platform/distribution_resources.txt`;
selection policy is in `egs/config/platform/distribution.yaml`. New runtime
resources must be explicitly reviewed and listed. The source archive includes the
build hooks needed to produce the same wheel without Git. Node module trees,
private configuration, environments, caches, databases and raw audit evidence are
excluded. Deployment documentation and dependency locks remain separate from
user credentials. The formal design is `doc/platform/installable_python_distribution_design.md`.

From a development checkout, `python scripts/packaging/refresh_resources.py`
checks for resource drift. `--write` writes a candidate inventory; review its diff
and scan new files before building. Private local overrides must stay excluded.
