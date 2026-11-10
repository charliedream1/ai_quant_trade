# Runtime selection and workspace layout

## Conda and PyCharm

Startup accepts dedicated virtual environments and non-base Conda environments.
Conda uses `conda-meta/history`, rather than `pyvenv.cfg`, for recognition.
Python support bounds and missing application dependencies are still checked.
Pinned-version and package-origin differences are reported as warnings so a
compatible user upgrade does not prevent PyCharm debugging. A clearly
incompatible major version remains a startup error. Conda base/root is rejected.

In PyCharm, select your dedicated environment's interpreter, set the working
directory to the repository root and run `start.py`. Optional script arguments
are `--host 127.0.0.1 --port 8000`. Terminal activation is unnecessary when the
IDE already runs the selected Python.

If `ALL_IN_ONE_WEB_ENVIRONMENT` is set in the process or local `.env`, it must
match the selected environment directory. Otherwise recognized non-base Conda
environments do not require a machine-specific prefix. Install the project
requirements yourself; preflight never installs or changes Conda packages. The
`==` pins in requirements and uv files document the tested baseline. They do
not turn the runtime check into an exact-version lock: compatible upgrades are
allowed and shown in the diagnostic report.

Run your interpreter with `egs/entrypoints/check_runtime.py --role web` to
inspect missing packages and compatibility warnings. pip/setuptools/wheel
version differences alone do not block application startup; installation
manifests retain their exact build-tool pins.

For pip, optional messaging and observation profiles have committed hash-locked
exports in `egs/requirements/channels.lock.txt` and `observability.lock.txt`.
They contain dependency versions and public package hashes, not credentials.

## Layout and reading

The shell and embedded modules use available viewport width with shared gutters.
Controls have consistent spacing and wrap on small screens. The AI conversation
fills its region; session/file sidebars can collapse.

The Learning Space has chapter navigation, previous/next controls and readable
body spacing. All quantitative chapters have maintained English counterparts;
language changes retain the selected chapter. User research documents and
entered messages retain their source language.

## ETF location

Open Strategy Build → Strategy Management → ETF Research. This panel retains
universes, fees, benchmarks, liquidity and source snapshots. ETF presets use
the normal strategy catalog and shared backtest flow. Old `view=etf` links open
the nested panel. ETF APIs and CLI commands remain available.

## Authentication output

Routine BaoStock login/logout success output is DEBUG. INFO retains business
outcomes; failures and unexpected provider output remain visible. The adapter
does not change error handling or credential storage.
