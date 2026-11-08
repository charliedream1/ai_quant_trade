---
name: quant-market-review
description: Use when the user asks for a dated market review, market breadth, sector rotation, or a market HTML report.
---

# 市场复盘

Use the existing platform workflow, not an independent LLM simulation. Locate the project root containing `egs/entrypoints/skills.py` and work there. See [the shared execution guide](../../../docs/usage/agent_cli_skills.md) for provider limits, data fields and research gates.

1. Read `egs/examples/skills_examples/quant-market-review.yaml`. Resolve the user's actual dataset/backtest ID, date, symbols, provider and budget. Example IDs are placeholders, not existing data. Ask only for information that cannot be found in the project or user request.
2. Create the task YAML inside the project; keep `skill: quant-market-review`. Credentials belong in project environment configuration, never in the YAML or prompt. Use the project's existing Python environment.
3. Run `python egs/entrypoints/skills.py preview --config <task.yaml>`. Use `providers --probe` when backend availability is uncertain. An installed CLI can still lack authentication or strict role eligibility; do not silently switch provider or relax permissions.
4. Run `python egs/entrypoints/skills.py run --config <task.yaml> --format jsonl` once. This is a foreground process. Preserve the returned run ID and actual events; use `show`, `events`, `files` or `cancel` with that ID. Do not launch recursive Skills from a model-provider subprocess.
5. Present the actual terminal status and HTML path. Distinguish protocol fixtures, real model calls and financial effectiveness. Do not fabricate AR/IC/drawdown, skip missing PIT evidence, treat unknown usage as zero, or claim research approval permits live trading.

Keep the existing economic/technical review and shared cost/risk ledger. When evidence is missing, report the missing fields and retain failed-run evidence instead of repeating paid calls.
