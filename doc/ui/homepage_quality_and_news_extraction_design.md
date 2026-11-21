# Homepage quality and news extraction plan

Date: 2026-11-20 (UTC+08:00). Status: implemented on 2026-11-21, with live BGE download awaiting operator approval.

## Code navigation index

CodeGraph 1.6.3 indexed an E-drive mirror of 827 tracked Python, JavaScript,
TypeScript and Svelte source/test files. The local SQLite index contains 14,713
nodes and 42,792 edges. The initial build took 23.1 seconds and the database
occupies about 50 MiB. A strict status check passed. Caller queries linked both
the sentiment radar and the theme summary to the homepage market loader and
showed the shared news loader's two homepage consumers.

This CodeGraph version accepts a directory name within its indexed project
root. The E-drive mirror keeps the database off the checkout drive. It uses
tracked working files, excludes local configuration and generated dependencies,
and runs with telemetry and file watching disabled. Refresh the mirror and
synchronize the index after edits. Create a new mirror for a new file inventory
when renames or removals would leave obsolete paths in the old mirror. Resolve
graph results back to the checkout using their repository-relative paths and
check current source before editing. Use the graph for symbols, callers and
impact analysis, and text search for YAML keys, CSS and literal UI strings.
Measure lookup latency and tool calls on a fixed set of tasks before reporting a
speedup. Application page latency has a separate acceptance baseline.

See the [CodeGraph CLI reference](https://github.com/colbymchenry/codegraph/blob/main/site/src/content/docs/reference/cli.md).

## 1. Language and button layout

The workspace runtime translates much of the UI by matching rendered DOM text.
Unmapped fragments in dynamic status messages, late updates and chart text
can survive a locale switch. The page Skill wrapper explicitly opts its
entire subtree out through `.no-i18n`, while its YAML labels are English.
The current language toggle also switches CN/US in some paths, which can
replace market data while the user is changing the display language.
An isolated Chromium run measured the English Refresh Overview button at
110 by 40 px with 56 px of scroll height at both desktop and mobile widths.
The homepage stylesheet fixes its width at 110 px. The same run showed the
English Skill accordion in the Chinese view. It found no Chinese text in the
other visible English homepage buttons, so the broader audit will cover
charts, dynamic states and the remaining pages.

- Inventory visible application controls, status/empty/error messages, options,
  chart labels and accessibility attributes in both locales. Start with Overview
  and Market Research, then check the shared navigation and button components.
- Render application-owned labels and formatted status messages from paired
  locale keys. Preserve original article titles, company names and identifiers
  as source data. Keep protected identifiers out of substring translation and
  narrow that protection to those fields. Cover both initial rendering and
  progressive updates.
- Separate display language from market selection. Test both switches across
  the shell and active embedded page without changing a selected item's ID.
- Fix the buttons identified by rendered measurements. Use natural widths,
  wrapping button groups or a concise localized label with the full accessible
  name. Preserve the styling of controls that already fit.

## 2. Market sentiment radar

`home_charts.py:sentiment_radar` builds one polar trace with three axes. The
index axis scales average reported index change into a 0–100 score. The breadth
axis uses the positive share of supplied sectors. The consistency axis is an
inverse range score. It can reach zero when the range is at least ten percentage
points. A large negative average index change can also clamp its score to zero.
A controlled input produced `[0, 50, 0]`. Both zero values sit at the origin.
Missing observations produce null points and leave gaps in the line. The real
HK provider currently returns an empty sector list.

- Keep the three-axis presentation and display a marker and numeric readout per
  dimension. Use a neutral unavailable state for null and show zero explicitly.
  Include sample size, source and observation time when available. Label the
  first axis as an intraday index momentum proxy and explain how dispersion is
  used in the consistency score. Preserve the current scaling in the first
  display change so score comparisons retain their meaning.
- The current input comes from a balanced gainer/decliner ranking. It can show
  50 percent by construction whenever both quotas are filled. Use a broad
  snapshot from the same market, universe and trading session for breadth and
  consistency when the provider supplies it. Count flat observations in the
  denominator and publish coverage. When only the ranked extremes are available,
  show them in the separate sector rankings and identify breadth and consistency
  as unavailable. Reuse cached source data and keep the provider budget bounded.

## 3. Topic and keyword extraction

`eastmoney.py:_keywords` returns early when a fixed finance term matches.
Otherwise it splits contiguous Chinese into two-to-four-character pieces by
regular expression. A probe split “多地密集推进城市更新改造工程” into
“多地密集”, “推进城市”, “更新改造” and “工程”, losing “城市更新”.
For a headline about semiconductor equipment and advanced packaging, the
fixed term branch returned only “半导体”. Homepage `theme_summary` counts
these stored tags over eight titles at most. `NewsAggregator.keyword_cloud`
counts the stored tags on a larger sample and currently ignores its requested
`scope` when selecting rows.

1. Implement a CPU baseline in the news service. Normalize Unicode, punctuation,
   tickers and case while preserving display spelling. Use precise Jieba
   segmentation and a small maintained finance dictionary with stop words and
   aliases. Use word boundaries for English. Generate actual noun phrases and
   event phrases from titles and useful summaries. Preserve source snippets.
2. Deduplicate syndicated stories before counting. Rank hot terms by distinct
   article and source support, title weight and source-time freshness. Compare
   domain TF-IDF with TextRank when evaluating candidate phrases. Expose
   mention counts and sample windows. Apply the same market, geography, topic
   and date filters in Overview and News Center. Support existing rows through
   lazy recomputation from original titles and summaries and version the
   cached extraction results.
3. Produce topics by grouping phrases and stories about an event or industry.
   Start with a finance taxonomy and alias rules. Report the representative
   headline, source time, supporting articles and confidence in the grouping.
   Preserve emerging terms without forcing them into known categories. Count
   each deduplicated story once in a topic even when sources repeat it.
4. Evaluate a small open embedding model as an optional second stage. Use
   BGE-small-zh-v1.5 (about 24M parameters, roughly 96 MB safetensors, MIT)
   to rerank existing phrase candidates and help merge similar stories.
   KeyBERT supplies a reference for similarity ranking and diversity.
   The extraction and ranking baseline remains usable when the model is
   unavailable. Keep model inference outside the UI callback and evaluate English
   coverage with its own fixtures before selecting an English model.

Compare against the current extractor on dated, deduplicated and manually
labeled CN/HK/US news examples, with the split by event so syndicated items
cannot cross from tuning into evaluation. Track top-10 precision, important
entity recall, duplicate rate, topic grouping errors and cold/warm CPU p95.
Enable model reranking only if it improves results within the measured latency
and memory budget. Verify Python 3.10–3.14 package support and licenses before
pinning any new dependency. Keep model weights and caches on the E drive.

References: [Jieba](https://github.com/fxsjy/jieba),
[Chinese keyphrase algorithm comparison toolkit](https://github.com/shibing624/pke_zh),
[KeyBERT](https://github.com/MaartenGr/KeyBERT), and
[BGE-small-zh-v1.5 model files](https://huggingface.co/BAAI/bge-small-zh-v1.5/tree/main).

## 4. Compact key news

The homepage fetch limit is eight and its renderer additionally clips the
feed to five individual cards. The backend already attaches geography,
finance/policy topics and source-time status. The homepage skips those fields
when grouping and rendering. The theme summary and news panel both use the
same raw-news helper, which offers a natural place to share preparation work.

- Start with a configurable target of 12–16 distinct stories when available.
  Give each nonempty geography/topic group a fair share, with a cap per
  source and event. Put each story in one primary group and retain its other
  topic as a label when useful. Support cross-border and unclassified coverage
  explicitly. Preserve the existing relevance filter.
- Use compact rows grouped into fewer containers, with headline, source and
  publication time. Allow summary expansion and link to the filtered News
  Center. Use responsive columns on wide screens and a single column on
  mobile. Distinguish unavailable providers from an empty time window.
- Share deduplicated news observations and update the panel progressively.
  Fetch bounded candidates per scope so busy categories cannot crowd out the
  rest. Keep source URL scheme validation and escaped presentation in the
  renderer.

## 5. Overview Skill entry

The module renderer mounts the report panel when a preset exists.
`page_analysis.yaml` associates `overview` with dashboard Overview and Custom
views, which explains why the control appears. This preset is also consumed by
the floating assistant for dashboard observations. Removing the preset itself
would affect that feature.

Prefer hiding the report action on Overview using an explicit presentation
flag or view restriction while retaining dashboard observation bindings. Keep
research/report actions on dedicated supported pages, with bilingual labels and
a preflight state tied to loaded evidence and provider availability. Preserve
access to reports already saved. The mock-data path reproducibly rejects native
Codex unless explicitly enabled. Missing/stale evidence and CLI availability
can also reject submission. Capture the actual failing action and error in an
isolated browser session before assigning the reported failure to a specific
branch.

## Delivery order and acceptance

1. Fix locale coverage and button layout, and place the Overview report action
   behind the appropriate view policy. Confirm retained assistant context and
   research-page reports.
2. Add the radar readouts and source/coverage states, then land compact grouped
   headlines. Verify using independent calculations for complete, partial,
   zero-valued and wide-dispersion inputs, including HK provider gaps.
3. Establish the segmentation baseline and hot-term/topic evaluation. Decide on
   optional model reranking from the measured comparison.

Verify actual browser clicks and locale round trips at desktop, 768 px and
390 px widths. Check titles, labels, keyboard accessibility, overflow and
progressive rendering before and after refresh. Verify underrepresented news
categories, duplicate articles, date boundaries and restricted provider
capabilities with controlled inputs. Compare cold/warm delivery of the existing
independent homepage groups. Record CodeGraph and application timing separately.
Run focused unit and integration tests on the approved implementation. Store
diagnostics and test files on E and stop only the test-owned listener.

## Approved BGE provisioning

The installer previews the model ID, pinned revision, download size and target.
It requests explicit operator consent before downloading. After consent it uses
a private staging directory, verifies file integrity, probes CPU inference and
publishes the model directory. It can persist the local mode and model path in
the workspace environment. A configured local ONNX directory or an
OpenAI-compatible remote embedding URL and bearer key can also supply vectors.
The optional runtime extra pins ONNX Runtime and Tokenizers. News pages can use
lexical ranking while a model is absent or unavailable. The home theme task
performs bounded reranking in the existing source worker so independent
account, index and sector results can arrive first.

The download artifact is the quantized Xenova ONNX conversion of the BAAI
model, pinned at revision `75c43b069aac4d136ba6bc1122f995fedcfd2781`.
Its tokenizer and weight total 24,449,967 bytes. Source URLs and consent
mechanisms are documented with the operator commands.
[Model files](https://huggingface.co/Xenova/bge-small-zh-v1.5/tree/75c43b069aac4d136ba6bc1122f995fedcfd2781).

## Implementation verification

The Windows Python 3.11 regression run passed 51 cases. The final affected
tests passed eight cases after the news query began selecting candidates
across classes. A separate browser test verified opening a research Skill,
generating a controlled report, previewing and downloading the HTML, and
reopening report history. The Overview browser test verified the refresh
button at 1440, 768 and 390 px, the locale round trip and market preservation.
Coverage focused on the affected pages and shared components.

The installer preview and EOF handling were exercised without approval.
Controlled files verified consent and integrity checks. A generated ONNX
fixture exercised the configured local directory, tokenizer and CPU
inference. A loopback HTTP service verified the embedding protocol and
bearer header. Real BGE inference and a representative labeled news quality
comparison require a separate acceptance run after download approval.

The lexical source code passed mypy, Ruff, reviewed Bandit and Gitleaks.
Both strict documentation builds passed. Dependency audit reported 44
advisories in three existing packages. Runtime acceptance used the E-drive
test dependency target, with analysis listeners stopped at test teardown.
