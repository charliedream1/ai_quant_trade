# Bilingual curated project resources

Date: 2026-11-19 (UTC+08:00). Status: implemented and verified with user-selected language subdirectories.

## Starting state and scope

The directory is named `awesome_projects`, rather than `awsome_project`.
Before the change it contained 15 English category files and an English directory
README. The three root READMEs linked to the same English resources. This is maintained
repository content, outside the MkDocs `docs/` source tree.

## Proposed document organization

Move the 15 existing category files into `awesome_projects/en/`, retaining their
filenames and English content. Copy the original index into `en/README.md` and
use the directory root `README.md` as a bilingual language gateway. Add matching
Chinese category files and an index under `awesome_projects/zh/`.
Each pair has an explicit English / Chinese language switch near its heading.
The language-specific category indexes and cross-category links keep readers in
their selected language. Shared repository resources keep their existing targets.
The user explicitly selected the `en/` and `zh/` layout instead of suffixes. Update
all maintained references to the moved category paths. No content is discarded and
no Japanese resource edition is introduced. Historical change logs remain history.

Translate all descriptions, headings, metadata labels, maintenance explanations,
adoption notes and navigation in the Chinese edition. Preserve project identifiers,
upstream URLs, licenses, historical star counts and stated verification dates.
Translations must not imply that metadata was researched again or that either
edition makes a different recommendation. Resource prose is intentionally Chinese
in the requested edition; implementation comments, plans and change logs remain
English.

The root English README links to the English resource edition and the root
Chinese README links to the Chinese edition. Both expose language alternatives.
The Japanese README identifies the available English and Chinese editions and
retains English targets for its existing category table. Do not duplicate the
resource collection into `docs/` or modify the application's language behavior.

## Validation and completion

Verify all 16 document pairs, matching project entries and external destinations,
language-specific relative links, language-switch round trips, UTF-8 integrity and
the three root README entry points. Render representative indexes and categories
to inspect Chinese/English navigation and layout. Run applicable documentation and
privacy checks and both strict MkDocs builds to check existing publication paths.
No production-code tests or dependencies are added for a documentation-only edit.

Record changed paths and acceptance in the weekly English change log. Preserve
unrelated staging and working changes. Temporary validation output stays on E;
owned preview services are stopped. No package changes, cleanup, commit or push
are included in this proposal.

## Verified results

There are 16 matching documents per language and one bilingual root gateway.
All 37 documentation checks passed: English source preservation, matching project
entries and external destinations, star/license/date parity, translated review
coverage, relative links, language switches, encoding and root README isolation.
The original staged patch was preserved exactly.

Offline Chromium replay passed gateway selection, per-category language changes,
same-language cross-category links, return-to-index navigation and desktop/mobile
preview checks. Preview rendering uses two-space list indentation and wraps long
project identifiers; these renderer settings do not alter repository or site CSS.
Representative Chinese index and category screenshots were inspected for readable
text and layout. Both strict MkDocs builds, resource secret scanning and Git
whitespace checks passed. No Python application, dependency or runtime behavior
changed, so application lint/type/dependency revalidation is outside this edit.

The metadata remains the original dated snapshot; external URL destinations were
compared across editions rather than queried for current availability or pricing.
No runtime service was started, and the owned headless browser exited. Evidence
and failed preview/check attempts remain private on E; no cleanup or publication.

## Publication review

The final review completed Chinese metadata wording for datasets, commercial data,
platform terms and benchmark groups, and clarified temporal link prediction and
multiple-reranker terminology. Historical licenses and facts retain their source
meaning. Publication excludes unrelated root README edits, local agent memories,
environment files and raw verification evidence. The user authorized commit and
push after the content and privacy checks; this supersedes the proposal's earlier
publication exclusion.
