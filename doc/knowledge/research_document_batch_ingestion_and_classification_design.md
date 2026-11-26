# Batch Research Ingestion and Classification

Date 2026-11-26 (UTC+08:00). Approved for implementation.

## Research selection

Add a shared batch import panel to report and paper search. Let the user
choose a destination library, select results across pages by title, or
prepare the full result set for the current filters. Show the source, filter
scope, available count, selected count, and known omissions before submitting
the job. Keep the existing single-document and abstract import actions
available and label their content coverage.

The report provider currently fetches its first page. Report details resolve
identifiers through the default report listing, which can omit records found
in a symbol-specific query. Paper search persists discoveries locally and
returns a paginated subset to the frontend. Use server-owned result snapshots
and the originating provider record for downloads. Capture the current market,
filters, source policy and result identity when preparing a batch, then keep
its membership fixed during execution and retry.

Selected results and each additional provider page use stable source
identifiers. Full import traverses the pages exposed by the source under the
current filters. Paper import covers the matching local discovery catalog and
the records made available by the configured provider query. Report the covered
scope explicitly if a provider caps, truncates or cannot enumerate results.
Display the limit and covered count when more work must be split into batches.
Prevent a refreshed query from silently changing a pending batch.

## Full-text import and job lifecycle

Use the existing bounded public-document downloader and parser to obtain
full text. Preserve original-file preview, chunking, provenance and current
retrieval projections. Identify inaccessible, abstract-only, scanned,
unsupported and malformed documents individually. A usable body is required
before a full-text import can succeed.

Resolve Eastmoney's original PDF from its published report page. The system
curl client can retrieve the same public HTTPS PDF when the primary transport
returns a web page. The alternate transport uses the validated public address,
enforces the document size and time limits and does not follow redirects.

Persist a background job and per-document outcomes so that the user can leave
the page, return to its progress, cancel remaining work and retry unsuccessful
items. Record completion, duplicate skips, unclassified review items and
failures separately. Reuse the application's task leases, download budgets,
process cancellation and scoped logging. Limit concurrency and use the
existing model gateway for remote requests and RPM. A download or
classification failure for one item leaves other items eligible to complete.

Deduplicate within a destination library by stable provider identity, canonical
work identifier where present, and exact content hash as a fallback. Keep
distinct editions when their upstream identifiers or document revisions warrant
it. Reuse a ready document on retry and protect concurrent jobs from publishing
duplicates. Allow multiple libraries to contain the same document. Preserve
completed work when a job is interrupted and show the status of any items
still awaiting completion.

## Classification modes

| Mode | Implementation |
| --- | --- |
| Traditional, default | Use a local TF-IDF classifier with Chinese word segmentation and character n-grams, English word features, and category examples declared in YAML. Evaluate it on separate labeled documents. |
| Local zero-shot | Use CPU ONNX inference with a local model path. The initial candidate is the multilingual six-layer MiniLMv2 NLI model and its community INT8 ONNX export, whose quantized graph is about 107 MB before tokenizer files. Score the configured category descriptions against a bounded text sample. Load the model on demand. [Model card](https://huggingface.co/MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli) · [ONNX export](https://huggingface.co/onnx-community/multilingual-MiniLMv2-L6-mnli-xnli-ONNX) |
| Configured language model | Use an enabled OpenAI-compatible model profile, existing rate limits and ordinary text generation. Parse the response with json-repair and validate category IDs against the configured taxonomy. Provide the current document title, abstract and bounded extracted passages. |

Let the user choose the mode per batch and set a default in configuration.
Keep labels, examples, thresholds, fallback rules, prompts and input limits in
YAML. Store service credentials in the existing local model configuration and
environment mechanism. Selecting a remote model displays the data scope for
that call. Use a fixed artifact revision and verified checksums for the local
model. A built-in download starts only after the user confirms its size and
location. A configured directory can use an existing model.

Assign a single primary category and optional controlled tags. Compare
confidence and ambiguity on held-out documents for each backend. Route
abstentions and classification failures to **Needs Review** with the reason.
Record the backend, model or classifier version, taxonomy version and manual
overrides. Apply a configured fallback only when requested and record which
backend provided the result.

## Knowledge library navigation

Organize documents under **Library → Reports or Papers → Topic**. Seed an
editable taxonomy with two topic levels, informed by JEL's economics and
financial economics groups and arXiv's quantitative finance categories. Keep
the research type separate from topic depth. [AEA JEL guide](https://www.aeaweb.org/jel/guide/jel.php?class=G&lang=en) · [arXiv taxonomy](https://arxiv.org/category_taxonomy)

| First level | Second level |
| --- | --- |
| Macroeconomics and policy | Economic cycles and inflation, monetary and fiscal policy and international economics |
| Company and industry research | Company financials and valuation, industries and supply chains |
| Investing and portfolios | Asset allocation and funds, factors and strategy backtests, asset pricing and derivatives |
| Trading and risk | Execution and market microstructure, risk measurement and hedging |
| Research methods and data | Statistics and econometrics, machine learning and financial data |

Expose publication year, institution, document type and topic as combinable
library filters. Use the provider publication date for year. For reports,
use the issuing institution. For papers, retain each author affiliation
supplied by the upstream record. Publication venues and distribution sites
remain source metadata. Missing dates and affiliations are filterable as
unknown. [Crossref metadata guidance](https://www.crossref.org/documentation/schema-library/required-recommended-elements/)

Keep storage keys independent of displayed names. Use the existing
category, tag and library mechanisms for browsing and retrieval. Category
assignment retains original document identifiers, sources and citations.

Add library, document type and category filters to the document list and make
new categories selectable in knowledge Q&A. Let a user change a document's
research topic. Preserve manual corrections through repeated imports. Hierarchy
membership and retrieval stay within the selected library and attachment
scope. Reuse SAG2 and zvec-grep for retrieval from the chosen scope.

## Acceptance

- Import one report from a symbol-specific result, several documents selected
  across pages and a full filtered set spanning multiple pages. Compare the
  expected membership and persistent job counts. Include provider truncation,
  empty results and query changes before and after submission.
- Verify mixed outcomes including successful imports, duplicates, missing
  full text, parser failure, low confidence, provider limits, cancellation,
  retry and restart recovery. Verify that concurrent imports and existing
  user assignments remain consistent.
- Benchmark the traditional, local and language-model modes on the same
  independently labeled Chinese and English collection. Report acceptance
  coverage, category accuracy, abstentions, runtime and local resource use.
  Exercise actual local inference after model availability is confirmed.
  Use a controlled service test for the language-model contract and a live
  profile when one is configured and approved for the test corpus.
- Exercise the complete workflow in the report, paper, library and Q&A pages
  with Chinese and English interfaces. Verify filtering, manual correction,
  original preview and citations after reclassification. Run relevant Ruff,
  mypy, tests, dependency and publication checks, and strict documentation
  builds. Record the tested Python and operating systems and stop test services.

## Verification record

Windows Conda Python 3.11 passed focused tests covering research ingestion,
local files, full-text downloads and SAG2. Chromium exercised report full-batch
submission and selected-paper submission and verified the resulting year and
institution in the library. Service tests exercised selection across report
pages, deduplication, manual classification, paper cancellation and retry,
multiple affiliations and combined filters. Live imports processed the original
Eastmoney report PDF and an arXiv paper PDF. The subjects matched company
financials and valuation, and asset allocation and funds, respectively.
The ONNX path executed on CPU with a local synthetic graph.
The language-model profile used a controlled generation response. Accuracy
with the optional production weights and real language-model profiles remains
to be measured. The legacy model-guided citation browser test reproduced the
same assertion failure on the pre-change checkout.
