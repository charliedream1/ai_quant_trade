# Installable Python distribution and runtime workspaces

Date: 2026-11-19 (UTC+08:00). Status: implemented and verified; local Linux execution remains unavailable.

## Observed constraints

The current project declares dependencies and the `aiquant` CLI entry point but
no build backend or explicit package/resource discovery. Its distribution name is
`b001-all-in-one`. The implementation uses the import namespace `src`; 92 of 581
Python modules reference the repository root. CLI serving imports the root
`start.py`, and configuration, examples, subprocess workers, documentation and
frontend assets rely on checkout-relative locations. A wheel containing only Python
files would install without providing a functioning standalone application.

## Compatibility and scope

Preserve the existing distribution identifier and `src.*` imports for this change;
document the distinction between the distribution name, import name and `aiquant`
command. Avoid a simultaneous business-module namespace migration. Support normal
wheel and source-distribution installation through pip and uv, as well as editable
development installation. Retain direct `start.py` launch and PyCharm debugging.
No public registry publication is requested.

Target the existing declared Python 3.10.1 through 3.14 range on Windows and Linux,
including standard venv and Conda environments. Do not promise unsupported Python
releases, operating systems, architectures or third-party worker capabilities.
Dependencies retain exact verified pins and conditional Python markers. Existing
optional SDK, model, observability, messaging and isolated-worker profiles remain
separate where their dependency constraints conflict. Package installation does
not silently install external executables or vendor account configuration.

## Build and resource boundaries

Declare an explicit pinned build backend and deterministic source/package inclusion.
Build wheel and sdist from an allowlist of maintained sources, license material,
public defaults, frontend assets and runtime support files. Include required
non-Python resources such as YAML, prompts, SQL, HTML/JS/CSS, fonts and WASM where
used. Dependency metadata and existing lock workflows must describe the installable
project consistently. Do not include local environments, `.env`, private overrides,
agent memories, tools, caches, databases, raw evidence, source-control metadata or
unrelated examples through recursive filesystem globbing.

Separate immutable distribution resources from writable application state. Resource
lookups must work after installation without a checkout or an assumption about the
current directory. An explicitly selected workspace supplies writable configuration,
data, logs, uploads and output. Keep credentials in that workspace's local `.env`;
do not search unrelated parent directories or modify installed package files.
Initial public defaults may be copied to a workspace without overwriting user
configuration. Source checkout operation retains its existing configuration behavior.

Audit root/path assumptions throughout startup, CLI contracts, help rendering,
default strategies, knowledge tools, workers and model/Skill execution. Use shared
path/resource helpers rather than per-feature guessed installation paths. Persisted
or copied configuration must resolve paths in the intended resource or workspace
scope. Missing optional tools and unavailable workers remain explicit capabilities.

## Startup and environment policy

Move reusable service startup into the installed package and retain `start.py` as
a compatible source wrapper. Existing CLI serving, REST/WebSocket routes, Gradio
assets and supported module entry points must resolve the same runtime settings.
Default non-strict startup permits compatible user-managed environments and reports
dependency differences. Strict verification remains opt-in and reads installed
distribution metadata/public runtime manifests rather than requiring a particular
checkout path or writable `site-packages`.

Document wheel/sdist/editable installation, pip and uv usage, workspace selection,
Conda/PyCharm debugging, strict/non-strict behavior, optional profiles and external
tool setup in English. Synchronize the root README entry points, dependency
declarations, relevant bootstrap/container/CI paths, specification and change log
only where affected. Preserve unrelated staged and working changes.

## Acceptance

Build wheel and sdist into private E-drive output; inspect their full manifests and
metadata for required assets, exact dependency markers and excluded private files.
Install the artifacts and an editable checkout into disposable E-drive environments
using pip and uv. Do not alter existing Conda environments or packages. Exercise
existing Conda interpreters through disposable installation targets where needed.

Use a working directory outside the repository, remove repository import-path
fallbacks and verify imported module locations. Test CLI help/contracts, service
startup, health/API/WebSocket endpoints, static assets, localization, help/default
configuration, database initialization, representative knowledge/strategy operations
and owned worker paths. Verify independent workspaces, restart persistence and
read-only installed resources. Controlled external services may validate contracts;
do not describe them as real provider acceptance.

Verify the available Python minor versions locally and add Windows/Linux installation
matrix coverage. Record unavailable interpreters/platforms honestly instead of
claiming unexecuted CI results. Run relevant unit/integration/browser tests, Ruff,
mypy, package metadata and privacy/dependency checks, plus strict documentation
builds. Stop owned services. Keep all installations, caches and temporary artifacts
on E; no user files are deleted. Commit/push requires a separate user request.

## Implementation

The pinned setuptools backend uses `setup.py` and
`scripts/packaging/build_support.py:ResourceBuild/PublicSdist`. Runtime assets and
public defaults are explicitly enumerated in
`egs/config/platform/distribution_resources.txt`; selection policy lives in the
adjacent `distribution.yaml`. Unlisted configuration is not implicitly packaged.
The archive includes its own build hooks and works without Git.

`core/paths.py` separates installed code, bundled public resources and the writable
workspace. Initialization copies public defaults without overwriting existing
files and rejects escaping resource/initialization metadata paths. Existing
root-relative lookups now use the shared workspace, and source fingerprints,
skills, assets and worker entry paths use the actual code installation. Paths
stored in configuration resolve relative to the selected workspace.

`src/startup.py` owns service launch, with compatible source `start.py`, installed
`aiquant-server`, `python -m src` and CLI serving. Source-launcher port-check hooks
remain compatible. Installed strict preflight reads distribution metadata;
non-strict editable environments report location differences without blocking a
compatible interpreter. Image IPC carries explicit workspace/policy data while
retaining isolated decoding. Strategy workers use the same interpreter and actual
code installation, including explicit installation targets.

`tests/packaging` verifies public inventories, source-workspace overrides, artifact
contents/metadata, repository-independent API/CLI/SQL/assets, knowledge TXT ingest
and SAG2 BM25 retrieval, a real strategy worker, help builds, read-only code and a
real installed-server browser page. The dedicated CI matrix covers the five
Python minor versions on Windows and Linux; local execution does not establish
that the hosted matrix has run. Source/editable installation retains its source
dependency by definition; wheel/sdist operation does not require the checkout.

## Validation boundaries and retained issues

Local Windows installations were exercised on Python 3.10.20, 3.11.14, 3.12.13,
3.13.15 and 3.14.7, with full version-pinned runtime environments. The existing
Conda interpreter was tested using an E-drive target, with its installed packages
untouched. The base profile does not imply that isolated Qlib/image or optional
model/CLI/Office capabilities exist in every environment. Linux execution is
unavailable locally because WSL lacks the required virtualization support and the
Docker daemon is not running; CI coverage is configured, not claimed as executed.

The source regression retains the pre-existing CLI mapping coverage check: the
HEAD route set with the unchanged catalogue maps 250 of 288 endpoints, below its
90% threshold. The working tree maps 252 of 298. The package does not weaken this
test or invent command contracts for unrelated pending endpoints. Offline command
loading and actual console entry points are validated independently.

An initial pip handoff omitted its cache override and created two small jsonpath
wheel-cache files on C. The dependency audit also used its independent default
cache. The private inventory records 45 task-created files totaling 436,022 bytes;
the user approved deletion, but automatic approval rejected the action with the
exact reason `blocked by policy`. The command did not execute: all 45 files remain
and no retry or alternate deletion tool was used. Subsequent installer, browser,
temporary and audit cache locations are set explicitly. Failed build and test
attempts are retained privately on E; they are not part of the distributions.

Executed Windows acceptance passed all five interpreter profiles, including SQL,
API, TXT ingest, BM25 retrieval, a strategy subprocess and local help generation.
Every minor also passed strict metadata checks and both console entry points.
Pip, uv, wheel, source archive and editable installation were exercised; the
final wheel passed read-only code and real browser tests in a fresh venv and an
existing Conda interpreter through an E-drive target. Source startup/environment
regression passed 33 cases, and artifact metadata/resource inspection passed.

Full source mypy, targeted Ruff/format, reviewed Bandit, secret scanning, exact
local-credential comparison and both strict documentation builds passed. Bandit
annotations explain fixed installer subprocess arguments and a display-only URL
alias, not executable user text or an added public bind. pip-audit timed out after
40 seconds and OSV Scanner was unavailable; existing dependency findings remain
unresolved. No existing Conda packages were modified and no user files were deleted.

Build implementation follows the official [Python packaging metadata guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
and [setuptools command customization](https://setuptools.pypa.io/en/latest/userguide/extension.html).
