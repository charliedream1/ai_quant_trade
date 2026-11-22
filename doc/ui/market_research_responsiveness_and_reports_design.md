# Market Research Responsiveness and Evidence Reports

2026-11-21 (UTC+08:00). Implemented for Task 6.

## Baseline and causes

- A real Conda session recorded about 6.0 seconds for the first overview task status, 10.1 seconds for headlines, 11.3 seconds for the account group, and 15.7 seconds for the market group. The next task-status read completed in approximately 14 ms after assignment. The code already separates four homepage callbacks. The account and market groups still use grouped delivery under the shared callback policy. The market payload also waits for news theme extraction before returning its full result, and the account group reads holding quotes before building its views.
- Three Conda browser baseline cases passed. The complete controlled homepage took 22.58 seconds on a cold visit and 0.89 seconds on cached return. The injected sector delay confirmed that the indices can already publish ahead of sectors and remain readable during sector failure and retry. The baseline records full completion; first-visible section timings are part of the implementation acceptance.
- The sector refresh took 20.5 seconds in the same session. The worker published the index table after about 15.8 seconds and the sector table after about 20.0 seconds. It currently forces an index refresh first, then requests the two ends of the sector ranking. Earlier Git versions also refreshed indices synchronously, so the timing alone does not isolate a version-specific regression. A separate live probe measured 4.70 seconds for indices, 5.13 seconds for industry and 2.55 seconds for concepts. The source reported rate limiting in all three requests. Industry returned 100 of 496 rows and concepts 100 of 554, so the bounded snapshot cannot establish full-universe breadth or both ranking extremes by itself.
- The sector service produces numerical gradient styles, and a controlled probe confirmed that positive, negative, zero and missing values survive conversion to the worker's table payload. The final browser rendering still needs inspection in both Gradio versions. The macro table currently returns a plain frame.
- The macro view loaded observations and built its table in the recorded session. Its later legacy economic report used the configured model API and failed with DNS error 11001. The sidebar CLI report is a separate path. A saved eight-series macro snapshot produced about 40,380 formatted characters before report framing, near the 48,000-character evidence budget. Report capture currently serializes the display table, plot and raw snapshot, and drops results above the budget.

## Overview and quote refresh

Use the existing page lifetime and cancellation machinery. Load local task state, stored account information, and the latest timestamped market snapshot independently of news and NLP. Show cash, positions and last recorded NAV from local storage, then reconcile live valuation as quotes arrive. Distinguish the stored valuation timestamp from live prices. Keep the current index, watchlist, breadth, sentiment, sector, task and account views accessible. Refresh the individual views when their own results arrive, including tables that become ready before plotting. Share raw news once per filter/window across headline and keyword processing. Store bounded source observations with market, source, scope, time, and freshness metadata. Expired data can appear immediately with an explicit stale state while the current request runs.

Separate local filter changes from a request for new observations. Reuse both directions of a fresh ranking when appropriate. Fetch a full source snapshot once only when supported and bounded, then sort it locally. Use verified descending and ascending source reads for partial universes and publish the first completed table ahead of its chart. Schedule independent index and sector requests with the existing provider admission and rate limits. A failed or slow index cannot prevent a sector result. Deduplicate refreshes and keep the previous timestamped rows during a refresh. The publishing path must reject superseded market, board, and tab revisions.

Apply a documented zero-centered scale to comparable percentage changes and show sign, value and units alongside the color. Respect the existing CN/HK presentation convention and give US polarity its explicit convention. Test computed styles and visible cells in both languages and themes, including scrolling and sorting. Add magnitude treatment to turnover where useful. For macro, display measured changes from the previous comparable observation or a defined threshold, with unit-aware scales. Present missing and stale values explicitly. A rise in CPI or yields describes direction by itself.

## Additional research information

| Priority and placement | Information | Source and eligibility |
| --- | --- | --- |
| Overview | Next scheduled macro releases, latest publication timestamp, recent threshold alerts, and coverage | Use the official calendar and the existing alerts store. Show actual and previous data when present. Show consensus or surprise only for a source that supplies the matching release and vintage. |
| Overview | Market participation, turnover relative to recent comparable sessions, and the strongest and weakest sectors | Display universe and session coverage. Full-universe participation requires verified full coverage. Cross-market funding or FX indicators belong behind optional cards with sources and time. |
| Stock analysis | Directional notes for trend, momentum, overextension and liquidity, plus 20- and 60-session relative performance | Reuse one timestamped chart snapshot and its matching benchmark or peer group. Explanations show the observed value, reference, timeframe and corroborating or conflicting evidence. |
| Stock analysis | Valuation and cash flow context, upcoming or recent company events, and source-linked disclosures | Load secondary data independently. Prefer reporting period, publication date and original issuer disclosure. Display peer comparison only when definitions and dates align. |

OpenStock uses index, heatmap, company and technical views. The open-source live-finance-dashboard demonstrates region and importance filters for economic events. The first implementation should integrate compact summaries into the platform's existing layouts. Statistics releases use the official calendar. Release and revision timestamps are distinct fields. [OpenStock](https://github.com/Open-Dev-Society/OpenStock) · [Live Finance Dashboard](https://github.com/artik0din/live-finance-dashboard) · [National Bureau of Statistics release calendar](https://www.stats.gov.cn/sj/fbrc/) · [FRED vintage dates](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html)

Technical explanations should make conditional interpretations explicit. For example, a positive MACD histogram describes momentum on the selected timeframe, while an elevated RSI can flag extension within an already strong trend. Treat insufficient lookback, suspension gaps, different adjustment factors and missing peers as explicit data limits. Separate indicator interpretation from model-generated reasoning in the interface through the existing analyst controls.

## Keyword extraction modes

- The default lexical mode uses Jieba and the financial phrase dictionary, followed by corpus TF-IDF for phrase candidates. Reuse the existing headline and recency weights, story deduplication, and distinct-source evidence. Use a configurable rolling corpus and a fixed rule for very small samples. Show representative headlines for each keyword.
- An explicit semantic mode reuses the local quantized BGE-small Chinese ONNX encoder and the approved OpenAI-compatible embeddings option. Build bounded phrases from source text and score their similarity to a story or topic centroid. Use KeyBERT's document-to-candidate comparison and diversity selection as design references. Compute only for the requested mode and show the effective backend and fallback state. Model directories, endpoints and secret references use the existing runtime configuration. Initial model download follows the user's prior explicit approval requirement. [Jieba](https://github.com/fxsjy/jieba) · [KeyBERT](https://github.com/MaartenGr/KeyBERT) · [BGE-small Chinese model card](https://huggingface.co/BAAI/bge-small-zh-v1.5)
- Compare both modes on the same frozen and manually annotated public news sample. Measure phrase accuracy, retained source evidence, duplicate rate, first usable keyword latency, warm latency and peak memory. Keep the news list independently responsive when the semantic worker is busy or a model is unavailable.

## Progress and CLI reports

Expose the worker's actual stages to the page, including queued, loading stored data, fetching the source, computing the view, and finished or failed. Prefer named stages and elapsed time for work that cannot reliably estimate completion. A section-level error retains the last displayed data and exposes retry. The report drawer uses the recorded task, provider, evidence and rendering events. Preserve the existing navigation cancellation and prevent stale stage events from overwriting the current page.

Expose a visible **Generate HTML report** action on each market-research surface and keep the existing sidebar entry. Reuse the same drawer, provider capability checks and model catalog. Tie the report request to the selected board/filters, company and timeframe, macro series, graph, pool, or recommendations, as appropriate. Use server-validated data and cite source URLs and timestamps. Send the bounded snapshot once. Save an immutable HTML artifact and provide preview, download and reopen through the existing history. The relation page can reuse the completed graph workflow with its current evidence model.

The macro page uses the shared CLI route for this action. Build evidence from the documented snapshot fields and representative recent observations per series. Show missing, stale or oversized evidence when it blocks a report. A configured API-based report displays its connection failure separately from macro data availability. Verify DNS failure handling with a local controlled fault. Never surface endpoint credentials or include them in reports.

## Acceptance

- Compare an isolated cold launch, warm page and repeat refresh in both installed Gradio versions, with the same source fixtures and network conditions. Record navigation-to-controls, first local data, first live rows, last section, queue delay and provider request count. Target visible feedback within 300 ms of an action on a mounted view and first local or cached content within one second of the active view mounting under the test fixture. Set no fixed time guarantee for uncached public providers.
- Delay news/model calls and verify independent account, task, index and sector results. Force provider failure and make sure existing rows stay readable and actionable. Verify industry, concepts, both directions, partial universes, scope changes and page cancellation. Check computed color, contrast, labels, stale and missing values.
- Exercise all market-research report entries with an isolated model fixture and verify that the selected scope persists and the saved HTML matches the download. Check real macro data and a verified local CLI from the normal route. Cover unavailable CLI, stale evidence, report cancellation, DNS failure and locale switching. Verify the semantic mode with an approved local model or a controlled local fixture if weights are pending approval.

## Acceptance results

The final controlled Conda homepage experiment measured 14.69 seconds to all sections and 0.63 seconds for a cached return, compared with 22.58 and 0.89 seconds in the baseline. An intermediate repeat measured 12.38 and 0.44 seconds. The project environment rendered all six plots and eight metric cards as well. The targeted real sector callback measured 10.34 seconds for the first industry request and 0.09 seconds for an immediate cached repeat. Concepts took 2.58 and 0.08 seconds respectively, with cached indices available in 0.02 seconds on the first concept request. Provider traffic and timing vary by network and observed market.

The real A-share probe produced 14 indicator and valuation rows, including two date-aligned relative returns. The macro browser probe loaded live macro data, displayed six tinted cells, then used the installed Codex CLI and downloaded the saved HTML. Both supported Gradio versions also passed controlled macro-report acceptance. Chromium verified the computed sector cell colors and opened an HTML report from a previously saved graph. Semantic phrase selection was tested with a controlled embedding response. Local model weights await separately approved download or operator configuration.

### WorkBuddy live browser acceptance

On 2026-11-22, Conda Python 3.11 and Chromium completed the relationship research flow using the installed WorkBuddy CLI and `hy4flash-free`. The live model catalog lists this model at `x0.00` credits. The project Skill read the official CATL and Stellantis announcement, extracted the partnership and checked its citations. The application classified the partnership as stated in the original. The first attempt completed both model stages, and the test incorrectly expected the label `fact`. The corrected test passed through graph preview and HTML export. Both calls on the passing run reported zero cost. The locally saved and browser-downloaded HTML matched byte for byte. The verified run took about 61 seconds from submission to download. [Original announcement](https://www.stellantis.com/content/dam/stellantis-corporate/news/press-releases/2024/december/10-12-24/en/EN-20241210-CATL-Stellantis-Joint-Announcement-Gigafactory.pdf)

A separate browser test bound the same WorkBuddy transport to the macro report provider slot inside the test process. The application read eight live series and generated four Chinese sections with evidence references. The one native call reported zero cost, and the HTML preview and download matched the stored report. October CPI and PPI values matched the National Bureau of Statistics release. The report identified the stale social-financing series. The macro request also carried a hidden default stock code, which the report correctly treated as irrelevant. The WorkBuddy transport was enabled through test configuration for this macro run. [Official October release](https://www.stats.gov.cn/sj/xwfbh/fbhwd/202611/t20261116_1965844.html)

### WorkBuddy in the page report selector

The page report drawer now lists WorkBuddy CLI separately from CodeBuddy.
It reads the configured WorkBuddy model catalog and requires an explicit model
selection. The drawer labels a zero-rate entry from provider metadata and
reports missing local settings. The report worker reuses the verified desktop
transport for current-observation reports, and passes the page's own Skill
prompt to it. The desktop runner validates model identity and native capability
events. Experiment review continues to require the strict research contract.

The installed WorkBuddy CLI passed a second browser run through the normal macro
report drawer without a test-only provider binding. The drawer loaded 57 models.
Selecting `hy4flash-free` used one call with zero reported cost. The resulting
Chinese report used eight live macro series and four sections. The preview and
download both used the stored HTML.
