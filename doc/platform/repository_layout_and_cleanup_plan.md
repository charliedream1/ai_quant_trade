# Repository Layout and Cleanup Plan

Date: 2026-11-07. Author: Codex. Status: migration in progress; delete candidates were authorized but automatic cleanup was blocked by policy.

## Objective

Reduce duplicate entrypoints, runtime clutter and ambiguous directory names without losing private configuration, historical changes, independent examples or callable interfaces. Preserve the current uncommitted SAG verification fixes and earlier pending platform features. No production source, environment file or directory is moved or removed during this audit. This plan contains no implementation code.

## Verified findings

| Area | Evidence and current purpose | Proposed treatment |
| --- | --- | --- |
| `.agents` | Eleven tracked files expose ten quant skills and a manifest mapping them to `src/skills`. This is host discovery/configuration, not a Python environment. | Keep the discovery location; retain one implementation under `src/skills` and the manifest-managed host wrappers. Verify generated-wrapper agreement. |
| `.cloudflare` | Two tracked files support optional Cloudflare Pages builds/deployment. The shell entry calls `scripts/build_docs.sh`; deployment guides and the publication checker reference it. | Keep provider-specific deployment configuration, consolidate generic build behavior under `scripts/docs`, and update documented commands. Do not assume whether a remote dashboard still uses the old path. |
| `.tools` | Local LibreOffice, zvec-grep, security scanner, Python runtimes, wheelhouses and caches. File parsing and lexical retrieval still depend on some of these paths. | Separate required local executables from disposable package caches. Move configured active runtimes to the E-drive development runtime root only after updating discovery/configuration. Do not move installed software into `src` or delete all `.tools`. Previously retained/rejected cleanup scopes remain outside this operation. |
| `.env` | The effective local variables were merged into one ignored root file and readers now use `.env`. The old `.llm_env` was removed after value verification; no secret value was printed. Keep a key-free `.env.example`. |
| Other environment-looking paths | Excluding dependency/cache/audit trees, the only additional file is a separate broker-research example's `.env.example`. Virtual environments and their metadata are Python installations, not duplicate variable files. | Keep independent key-free examples unless the corresponding example is retired. Never bulk-delete files by matching the word `env`. |
| `changelog/platform` | Historical duplicate-week storage remains on disk because the approved removal command was blocked by policy; the migration rationale is documented. | Entries have been merged into the root week where possible; keep the old folder until cleanup can be completed safely. |
| `changelog` | Twelve Markdown files, 2,625 lines, all contain Chinese. | Convert all prose/headings to English, keep original dates, identifiers, code paths, function names and results; normalize the month-local Monday-to-Sunday week convention. Do not invent missing author/time information or rewrite historical outcomes. |
| `doc` | Thirty-four tracked formal specifications/designs; existing repository conventions designate it as the internal design source. | Keep formal design documents, group by platform, data, knowledge, models, strategies, security and operations. Replace numeric-only naming with meaningful filenames, updating references. |
| `docs` | Public MkDocs source, usage/principles/platform landing pages, older environment/FAQ/deployment material, research/reference, compatibility pages and private audits. | Keep usage, principles, platform, assets, deployment and environment topics clearly separated. Relocate historical drafts into a non-published archive. Preserve compatibility redirects where links remain. Do not modify any `docs/task*.md` file; exclude private audit/runtime data from both builds. |
| `egs` | 184 tracked files and 70 live root files. This includes production YAML, prompts, templates, entry scripts, fixtures and dependency profiles; many are actual runtime inputs. | Classify by purpose and domain before moving. Do not interpret low direct import counts as proof that a YAML/template is unused. |
| `egs_aide/看盘神器` | Nineteen files, 98,755 bytes; all are Python bytecode under `__pycache__`. No source or original document remains in that tree. | Approved cleanup candidate: remove this obsolete cache-only tree after confirmation. It is not another complete Chinese edition of the English project. |
| `egs_aide/excel_stock_monitor` | Maintained example with real source, dependency profiles, nested tests and media. | Keep it; group example/media/test assets without deleting non-English documentation merely because another filename is English. |
| `scripts` | Three tracked files provide cross-platform documentation build entrypoints and instructions. | Keep entry scripts; group documentation commands under `scripts/docs`. |
| `site` | Untracked generated HTML/search/assets and local server logs. `mkdocs.yml` writes here; application help normally uses `data/help_site` instead. | Rebuildable cleanup candidate after checking active consumers. Direct new local output to an E-drive build directory; keep CI output names compatible with deployment configuration. |
| `snippets` | Two tracked README introduction fragments. No active MkDocs include is enabled; publication checks explicitly prohibit the obsolete include mechanism. The files contain synchronization comments rather than an active build reference. | Deletion candidates after final backlink review; preserve any unique prose in the maintained README/docs first. Treat `docs/snippets` separately. |
| `tools` | Nineteen tracked old utility/config/hook files: dates, file helpers, plotting, stdlib logging and an old Flake8 hook. Some have independent legacy example copies under nested `src/tools`. | Refactor reusable functions into domain-appropriate existing `src` modules; replace old logging with Loguru; move developer hooks to `scripts/quality`. Do not mass-replace every `src.tools` import because nested projects own those namespaces. Remove root `tools` only after direct and transitive callers are updated and checked. |
| `tests/legacy/momentum_rotation` | One genuine momentum-rotation test module plus three CSV fixtures and a README. It targets `egs_trade/vanilla/momentum_rotation`; it is not a duplicate of the current platform test suite. | Merge under `tests/legacy/momentum_rotation` and update fixture lookup, discovery and invocation docs. Preserve behavior and isolation from unavailable market/model services. |
| `scripts/docs` | Four tracked publication/language checks, directly referenced by MkDocs hooks, CI, shell/PowerShell builds and deployment guides. | Move to `scripts/docs` with adjusted import/root discovery, CI paths and hook references. These are active build tools, not unused scratch files. |

Tracked counts describe Git-managed files; live roots can additionally contain ignored settings and untracked task work. Dependency, cache, audit and runtime trees are intentionally excluded from the environment-variable file count. No credential values appear in the inventory or this plan.

## Proposed target organization

The user explicitly clarified that `doc` and `docs` must remain sibling directories at the repository root. Neither may be nested inside the other. Classify their own contents by responsibility; do not create `docs/doc`, `docs/design` as a replacement for `doc`, or `doc/docs`. The formal design catalogue belongs to `doc`; published user-facing material belongs to `docs`.

Within `doc`, use platform, data, knowledge, models, agents, strategies, security and operations groups. Within `docs`, retain usage, principles and platform entrypoints; consolidate environment, FAQ, community and deployment material into explicitly named groups, and isolate historical drafts under a non-published archive. Leave `docs/task*.md` unchanged. Existing language variants remain associated with their topic; their language does not decide whether the underlying content is obsolete.

| Root | Responsibility and grouping |
| --- | --- |
| `src` | Production modules; reuse current `core`, `data`, `documents`, `knowledge`, `observability` and frontend boundaries. Add narrowly named I/O/date/chart helpers only where functionality is missing. |
| `egs/config` | Runtime YAML grouped by platform, models, agents, knowledge, data, strategy, execution, security and UI. Prompts remain external configuration in their corresponding domain. |
| `egs/examples` | Strategy, pipeline, skill, research, file-preview and resource-pool examples with their required datasets and manifests. |
| `egs/entrypoints` | Thin launch/setup/check/worker entry scripts. Preserve documented root entrypoints only when a compatibility shim is required; retire shims after callers are migrated. |
| `egs/requirements` | Versioned dependency profiles and hash locks, retained as a distinct category. |
| `doc` | Internal, English formal design/specification documents grouped by domain; no implementation code. |
| `docs` | Published usage/principles/platform/deployment material and assets; explicitly non-published research/reference/archive/audit areas. |
| `tests` | One test root, including migrated legacy momentum tests and fixtures. Keep fixture ownership close to its test category. |
| `scripts` | Cross-platform developer/repository operations grouped into documentation, quality and migration operations. No application business logic. |
| `changelog` | English month/week logs in one directory. Imported historical entries are merged, not discarded. |
| `.env` | The single real root variable file, ignored by Git. Root `.env.example` remains safe documentation of available keys. |

Independent educational/example roots such as `egs_trade`, `egs_data` and `egs_llm` are existing separate projects. This pass audits references but does not flatten all those projects into the platform's `src` tree or remove their independent dependencies.

## Root-file assessment

Keep the README language variants, license/contribution/conduct files, `AGENTS.md`, `start.py`, `pyproject.toml`, dependency profiles, `uv.lock`, MkDocs configurations, Read the Docs configuration, Git ignore/attributes and Gitleaks policy. They are runtime, packaging, collaboration or publication contracts.

`update_log.md` is empty and is a deletion candidate. `radio_relation.png` is a loose root image needing a final reference check and either relocation to the appropriate asset directory or deletion approval. `.clang-format`, `CPPLINT.cfg`, `.flake8` and `.pylintrc` are legacy tool configuration; no tracked C/C++ sources were found in the initial extension scan, while the current pre-commit file still contains old Black/Flake8 configuration. Verify hook/CI/editor consumers before retiring those configs and synchronize the actual Ruff/mypy/pytest workflow.

Generated `runtime` logs, Python bytecode, tool caches and editor metadata need an explicit private cleanup inventory. Existing Conda/venv installations, backups, raw evidence, `.workbuddy` data, downloaded original documents and previously retained/rejected cleanup paths are preserved until a separately authorized retention decision. The plan never removes a directory merely because it is hidden or ignored by Git. Automatic review blocked the approved cleanup commands; the affected paths remain and were recorded in the audit report.

## Migration and deletion gates

1. Record a source/index manifest and path mapping, preserving unrelated pending work and Git staging.
2. Merge effective local environment values without printing or committing them; verify process/YAML precedence, UI save/import/remove behavior, redaction and credential protection.
3. Consolidate logs and documentation/build checks, update all internal links/nav/hooks/CI paths, and preserve restricted task documents.
4. Move classified configuration/entrypoints using a central path resolver where necessary; update workers, CLI, skill manifests, package data and tests in the same change.
5. Refactor root utility behavior by domain and merge legacy tests, distinguishing nested example namespaces from the platform's imports.
6. Review each obsolete path against the completed mapping. Delete only paths explicitly approved by the user; verify no unique source/configuration/history is lost.
7. Run scoped unit/integration/legacy tests, configuration/CLI/worker and browser smoke checks, both strict MkDocs builds, link/publish-scope checks, Ruff, mypy, dependency/security and UTF-8 checks. Record pre-existing limitations separately. Stop test-owned services. No push.

Before implementation the user approves this concrete plan and the clearly bounded deletion candidates. Additional obsolete files discovered during migration are listed for a separate deletion decision; they are not silently added to the approved scope. No new permission request is needed for routine edits already included in the approved migration scope.
