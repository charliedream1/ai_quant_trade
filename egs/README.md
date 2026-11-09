# Example configurations and entry points

`egs/` contains runnable examples and configuration templates for the integrated
platform. It is kept separate from `src/`, which contains reusable application
code. Every example is UTF-8 text and uses relative paths so that a fresh clone
can be started on Windows or Linux.

## Directory map

| Directory | Purpose | Typical command |
| --- | --- | --- |
| `config/` | Versioned YAML defaults grouped by agents, data, strategies, models, knowledge, operations, platform, security, UI, and CLI. | Set `ALL_IN_ONE_*_PATH` or copy a template to the local `.env`. |
| `examples/` | Small strategy, skill, alpha-mining, resource-pool, file-preview, and data fixtures. | Pass the YAML file to the corresponding CLI command or API upload. |
| `entrypoints/` | Thin executable adapters for the CLI, workers, runtime checks, document preview, knowledge search, skills, and messaging gateway. | Run `python egs/entrypoints/check_runtime.py --role web`. |
| `requirements/` | Exact direct requirement profiles and generated hash-locked exports. | Install `runtime.lock.txt`, `runtime-models.lock.txt`, or an optional profile in a dedicated environment. |

## Common examples

```powershell
# Verify the selected environment before starting the service.
python egs/entrypoints/check_runtime.py --role web

# Start the integrated service.
python start.py --host 127.0.0.1 --port 8000

# Inspect the available strategy composition templates (requires a running service).
python egs/entrypoints/cli.py pipeline templates --format json

# Install the optional lexical knowledge search package into the E-drive tools directory.
python egs/entrypoints/setup_knowledge_search.py
```

The bootstrap command in `scripts/setup_project.py` creates the selected
environment, cache, temporary directory, and activation files outside the
checkout. Source the generated activation file before using an `egs` entry point.
The root [installation guide](../docs/usage/installation.md) explains the `pip`
and `uv` profiles. Optional Qlib, image validation, messaging, and observability
profiles must remain in their own environments when their lock files require it.

Do not put credentials in this directory. Copy `.env.example` to the ignored
root `.env` and configure provider keys there.
