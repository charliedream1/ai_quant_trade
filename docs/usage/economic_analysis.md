# Macroeconomics and corporate fundamentals

Open **Market Research → 宏观经济** or **Market Research → 基本面分析**. These views support Chinese macroeconomic data and A-share companies. Data and calculations work without a configured model. Navigation does not fetch economic sources or generate a report.

## Read macroeconomic evidence

Choose series and click **读取数据**. Enable **强制更新来源** only when a new source fetch is needed; the default source cache lasts six hours. Each trend has its own axis and unit. The overview shows the observation period, measurement basis and stale-data state.

| Series | Meaning and unit |
| --- | --- |
| GDP | Cumulative year-on-year growth, percent; quarterly frequency |
| CPI / PPI | Year-on-year price changes, percent |
| Manufacturing PMI | Index level, not a growth percentage |
| M2 | Year-on-year money-supply growth, percent |
| Social financing | Monthly increment, CNY 100 million |
| LPR | One-year and five-year annual rates, percent |

Eastmoney and MOFCOM are identified as the actual upstream sources. Publication timestamps remain unknown when the source does not supply them. Observation dates represent source period anchors, not release dates. A stale source remains visibly stale; the application does not replace it with invented current data.

## Inspect company fundamentals

Enter an A-share code or a recognized company name. Leave the report-period field blank for the latest available period, or enter a calendar-quarter endpoint such as `2025-12-31`. Optional peers are comma-separated and limited to five. Click **读取数据**.

The table combines income, balance-sheet and cash-flow summaries with reported financial indicators. Raw amounts use CNY. Reported gross margin and weighted ROE use percentages and retain their provider definitions. Values that cannot be calculated stay missing.

Selecting a report period also limits the displayed history and report evidence to that endpoint. Security aliases do not create duplicate peer samples. If a controlled integration supplies simulated source data, the snapshot and report retain the simulation marker; a simulated peer also marks the combined comparison as simulated.

Single-quarter values require the previous cumulative period within the same year. TTM requires four consecutive quarters. Growth percentages require a positive comparable base; zero and negative bases have explicit states. Financial institutions require specialized methods, so generic industrial-company margin, ROE and debt judgments are withheld. A disclosed borrowing/bond subtotal with incomplete components is never presented as total interest-bearing debt.

Peer comparisons include only matching industry and reporting period. Inspect the actual sample and gaps rather than interpreting it as an industry ranking. Current PE/PB comes from a separately dated quote and is unavailable in mock quotation mode; it cannot establish a historical valuation percentile.

## Generate and reopen a report

After loading data, choose a model API configuration and click **生成模型分析报告**. The report consumes the selected immutable snapshot, retains source references and explains evidence gaps. The new tasks use the shared OpenAI/LiteLLM client and RPM controls described in [Model interfaces](model_interfaces.md).

The page shows actual execution status, an embedded HTML report and a download. Keep the run identifier to reopen the same report using **重新打开报告**. The existing report library also retains insight runs. A `partial` state preserves research limitations and does not mean that missing financial data were filled in.

Existing individual-stock reports may request statement evidence through the `include_fundamentals` option. The separate fundamental task accepts a frozen `research_snapshot`, avoiding an unintended refetch during report generation.

For an individual-stock report, `research_snapshot` can also select a compatible frozen financial snapshot. Without one, current statement collection is allowed only for current research dates. Historical requests preserve an evidence gap instead of attaching today's financial revision.

## API and CLI

The REST endpoints are `GET /api/v1/economics/macro`, `GET /api/v1/economics/fundamentals/{symbol}` and `GET /api/v1/economics/snapshots/{identifier}`. Macro queries accept `series` and `refresh`; fundamental queries also accept `period` and `peers`. Unsupported markets use the platform's existing business-error envelope.

```bash
python egs/cli.py economics macro --series cpi,pmi
python egs/cli.py economics fundamentals 600519 --period 2025-12-31 --peers 000858
python egs/cli.py economics snapshot SNAPSHOT_SHA256
python egs/cli.py insight run --kind fundamental_analysis --symbol 600519 --research-snapshot SNAPSHOT_SHA256 --model-id 1 --stream
```

Replace the snapshot placeholder and model identifier with actual saved values. CLI calls use the same backend service and data contract as the page.

## Storage and research boundaries

Private raw revisions, source caches and derived snapshots live under the configured data directory's `economics` folder. Source requests have configured time, byte and row budgets. Cached revisions retain their earliest observed time; refreshed revisions receive separate hashes. A digest check detects changes to a saved snapshot.

Current public revisions are marked `historical_pit_eligible: false`. A historic announcement date does not prove that today's revised values were known at that date. Past-date report requests that precede the snapshot are rejected. For historical experiments, continue using separately verified data in [Alpha research](alpha_mining.md).

All source mappings, units, cache settings and limits are in `egs/economic_analysis.yaml`; prompts remain in YAML and the project-local economic analysis method document. No paid feed or new Python dependency is required. Source availability and freshness can change independently of the application.

See [Economic research principles](../principles/economic_analysis.md) for accounting and provenance details.
