# Stock relationship graph validation

Validation uses explicitly synthetic protocol/lifecycle fixtures separately from
actual corporate originals and WorkBuddy Hy3 calls. Real acceptance reads original
documents through the production downloader, executes the versioned Skill workflow
and validates/reviews the generated graph. Browser checks reopen saved artifacts
without substituting fixed model answers into the live run.

The opt-in test is `tests/engine/test_model_graph_live.py`, with cases in
`tests/engine/model_graph_live.yaml`. Set `MODEL_GRAPH_LIVE=1`, a private
`MODEL_GRAPH_LIVE_OUTPUT` directory and the WorkBuddy environment references from
the [usage guide](model_stock_relationships.md). Optional
`MODEL_GRAPH_LIVE_CASE` selects one configured case. A normal pytest run skips
remote model generation. Keep actual source snapshots and raw run evidence outside
published documentation.

The fixed-source gold checks are deliberately small:

| Target | Original | Required interpretation |
| --- | --- | --- |
| CATL, CN 300750 | [Joint CATL/Stellantis announcement, 2024-12-10](https://www.stellantis.com/content/dam/stellantis-corporate/news/press-releases/2024/december/10-12-24/en/EN-20241210-CATL-Stellantis-Joint-Announcement-Gigafactory.pdf) | Joint-venture partnership; planned/conditional factory, not proof of production or deliveries |
| Tencent, HK 00700.HK | [Ubisoft closing announcement, 2025-11-21](https://staticctf.ubisoft.com/8aefmxkxpxwl/75tVaQDaf9A5X8N97roq4K/5fc21239bb19bfc7ee1a8599a216e1fc/Closing_press_release_21.11.25_EN.pdf) | Tencent→Vantage Studios minority economic interest; Ubisoft retains exclusive control |

These cases test citation matching, link semantics and direction, not complete
coverage or continuing validity of the issuers' relationships. The production
workflow must reject unsupported extraction rather than increase graph density.

Initial acceptance exposed publisher HTTP 403, PDF quote/partial-date drift and
WorkBuddy native-flag/schema differences. Failed attempts were retained separately.
The working profile requires empty tool/MCP manifests; this WorkBuddy schema omits
optional Skill/plugin counts, which remain unknown. Exact quote checks were kept,
and one corrective extraction was added inside the original total-call budget.
Repeated PDF typography drift led to numbered frozen quote spans: the model
selects an ID and the platform fills the original text without rewriting it.

## Actual Hy3 results, 2026-11-14

| Case | Retained claims | CLI calls | End-to-end time | Reported cost |
| --- | --- | --- | --- | --- |
| CATL / Stellantis | 2 | 2 | 100.515 s | USD 0 |
| Tencent / Vantage / Ubisoft | 3 | 2 | 87.188 s | USD 0 |

Both required gold relationships were recovered. Manual review found the five
retained source claims supported by the supplied originals, with correct
direction for investment/control and the supply intention. All eight cited
spans matched their frozen text exactly. The CATL supply edge explicitly describes
a non-binding MOU and does not establish deliveries. The Tencent investment
preserves 26.32% economic interest and Ubisoft's continuing exclusive control.
The displayed claim classifications describe source statements, not a guarantee
of current business status.

The four calls reported 30,512 input tokens, 11,707 output tokens and USD 0 total;
one call also reported 3,328 cache-read input tokens. These are CLI-reported
counters, not an independent billing measurement. The successful profile exposed
no native tools/MCP. Optional Skill/plugin counts were not reported by the CLI.

The browser reopened both actual results on a desktop viewport and a 420-pixel
mobile viewport, expanded frozen originals, switched language without rewriting
evidence and downloaded byte-identical immutable JSON. Reopening/export used no
additional model calls. A translation defect found during acceptance was fixed
by excluding the English research/evidence panel from automatic substring
translation. The model view preserves business labels and directions and omits
invented price-change/strength metrics.
An additional controlled browser run exercised the Generate button, observed
completion, started another run and cancelled it through the page. That lifecycle
check uses an explicit synthetic generation fixture; the corporate-source cases
above use actual Hy3 generation.

Synthetic checks cover unknown/altered quote IDs, original quote drift, future and
undated historical evidence, invalid intervals, disconnected filters, review
failure, document sessions, public-network/origin controls, bounded ReAct source
discovery, Skill execution, subprocess capability rejection and cancellation.
The existing rule graph remains covered separately.

This is a two-original acceptance sample, not a market-wide precision/recall
benchmark. Autonomous web-search quality, other models, live Qoder generation,
historical point-in-time suitability and continuing validity remain unverified.
Broader legacy regression also exposed existing E-drive evidence-directory
restrictions in generic ProviderClient tests and a composition report-path
failure; these are separate from the passing graph workflow. Dependency audit
exceeded its 30-second budget, and OSV Scanner was unavailable. No dependency
versions were changed.
