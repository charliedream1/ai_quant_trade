# Python Compatibility and Unified Langfuse Observability

Status: approved by the user on 2026-11-04; implementation and local acceptance completed on 2026-11-05. This document contains design decisions and acceptance criteria, not implementation code. Existing uncommitted strategy/backtest work is preserved.

## Objectives

Support the integrated source workspace on standard 64-bit CPython 3.10 through 3.14 wherever dependency installation and behavioral verification succeed. If 3.14 cannot pass, lower the advertised upper bound to the highest consecutively verified version. The README badge must identify an explicit tested range rather than implying support for all future Python releases.

Extend optional Langfuse observability from the existing GenericAgent-only adapter to common language-model calls and agent workflows. Existing ordinary OpenAI-compatible generation, JSON repair, textual ReAct, SDK selection, quotas and execution semantics remain the behavioral contracts.

## Findings from the current repository

| Area | Verified condition | Required action |
| --- | --- | --- |
| Python metadata | Project minimum, runtime preflight, Ruff and mypy currently target 3.11 | Align declarations with actual accepted versions |
| Runtime APIs | Multiple source modules import datetime.UTC; runtime preflight imports tomllib | Use compatible UTC access and a conditional TOML reader on 3.10 |
| Syntax | Source and entry/example files parse with Python 3.10 grammar | Verify imports and runtime behavior separately; parsing alone is insufficient |
| Numerical dependencies | Installed NumPy 2.4.6, SciPy 1.17.0 and scikit-learn 1.8.0 require 3.11 or later | Use tested conditional pins for 3.10 and retain compatible newer pins elsewhere |
| Existing observability | GenericAgent wraps agent, generation and tool observations | Reuse the adapter while extending coverage and preventing duplicate generations |
| SDK installation | Langfuse 4.17.0 is declared as an optional extra but absent from the current project environment | Install and test the real optional SDK in project-owned environments |
| Privacy | Existing agent metadata includes the absolute workspace path; exception status includes raw exception text | Apply metadata allowlists and redaction before export |
| Local service settings | No Langfuse endpoint or project credentials are configured | Validate SDK export locally; distinguish this from a real Langfuse dashboard acceptance |

The dependency candidates for 3.10 are NumPy 2.2.6, SciPy 1.15.3 and scikit-learn 1.7.2. They remain candidates until actual installation, behavior and security checks pass. Other transitive dependencies are resolved with matching interpreter/platform markers. No environment name or successful resolver output is accepted as a substitute for execution.

## Compatibility boundaries

The primary acceptance covers the Web/API/CLI application, knowledge processing, agent/model adapters and supported strategy calculations. Optional CPU models, Qlib and image workers have explicit capability rows. A main application running on 3.10 may use an independently verified worker interpreter for an optional backend whose dependencies require a newer Python. Such a worker requirement must be visible in installation instructions and cannot be hidden behind the primary badge.

Use existing interpreters without modifying them. Create additional environments, dependency caches and any required interpreter installation only inside this repository. Preserve the existing project environments and previous temporary artifacts. No Conda package source or other project is modified. New compatibility environments remain excluded from Git.

Synchronize pyproject metadata, root requirement files, applicable lock files, runtime environment checks, installation/preflight instructions and all three README badges. Retain existing README update-table placement. Do not modify historical task documents or unrelated legacy examples as a broad cleanup.

The intended accepted range is at least 3.10 through 3.13, with 3.14 attempted first as the upper endpoint. An unsupported version receives a concrete installation or behavioral failure record. Documentation distinguishes Windows execution evidence, Linux CI configuration and any Linux execution evidence actually obtained. An unexecuted CI definition is not reported as a passing Linux test.

## Shared observation architecture

A project YAML configuration owns monitoring options, including enablement, sampling, content capture, batching, export timeout and environment labels. Credentials and the selected service endpoint are loaded only from local environment configuration. Monitoring is disabled by default. Missing configuration or SDK availability produces a clear no-op status; it does not prevent model generation.

The common model boundary creates generation observations for HTTP, OpenAI SDK and LiteLLM SDK requests. Associate the selected model, backend, purpose, actual reported token usage, latency, retry count and quota waiting time. Track individual attempts without counting one logical generation twice. Provider errors and cancellations receive explicit completion status. A failure in telemetry initialization, observation updates, export or shutdown must not change the original model result or error.

Legacy SSE generation and native CLI providers require their own boundary coverage because they can bypass the common nonstreaming client. Streaming observations close on completion, failure or cancellation. Native providers record the enclosing invocation and only metadata exposed by the actual CLI response; internal provider tokens, cost and tool operations remain unknown when not reported. They must not be fabricated.

Agent roots and child steps cover GenericAgent, research/decision teams, strategy-agent sessions and knowledge retrieval/tool loops. Generation observations join the active workflow trace. Carry correlation context explicitly across application thread pools and task boundaries, and verify concurrent workflows remain isolated. Reuse existing observation contexts and retain compatibility with the old GenericAgent enablement configuration without creating duplicate roots or generations.

SDK initialization, batching and application shutdown are centralized. Avoid forcing an exporter flush for every model call. Expose a minimal configuration/health summary and trace identifiers or links where available, without returning credentials. A status read does not silently send a request to an external monitoring service.

## Privacy and operational behavior

Metadata-only capture is the default. Prompts, responses, retrieved documents, tool arguments/results, attachment contents and absolute local paths are excluded unless their documented capture option is explicitly enabled. API keys, authorization headers, credential-bearing URLs and environment values remain excluded even with content capture enabled. Use existing redaction facilities and sanitize exception information before observation updates or logging.

Export only the application observations required for the feature; do not enable global automatic HTTP/database/process instrumentation that could collect unrelated data. Configure the actual selected Langfuse endpoint explicitly. Existing public-model transport protections and RPM accounting must remain intact.

## Planned change locations

| Workstream | Main locations |
| --- | --- |
| Compatibility and locks | pyproject.toml, requirements.txt, requirements-models.txt, uv.lock, egs/requirements, egs/config/operations/runtime_environments.yaml |
| Runtime compatibility | src/core/timeutil.py, src/core/runtime_environment.py and source/test modules importing 3.11-only APIs |
| Observation configuration | New project YAML configuration, local environment variable documentation and optional dependency profile |
| Common model observations | src/agent/llm_client.py, model_calls.py, langfuse_observer.py and shared provider adapters |
| Agent hierarchy and streaming | GenericAgent, research/decision teams, agent-strategy sessions, knowledge retrieval and src/engine/insights/backend.py |
| Lifecycle and status | Existing application startup/shutdown and model/monitoring status surfaces |
| Documentation and verification | English usage/principle documentation, three README update rows/badges, compatibility/observation tests, applicable CI matrix and monthly-week changelog |

Implementation should prefer small shared modules and narrow entrypoint instrumentation over copying exporter logic into individual strategies.

## Acceptance

1. For each target Python version: resolve and install the applicable pinned profiles into an isolated project environment, run package consistency checks, import/start the application, and exercise representative API/CLI, knowledge, model and strategy paths. Run broader regression on the established environment and relevant endpoint versions. Record unsupported optional capabilities separately.
2. Verify the real Langfuse SDK exports correctly formed observations to a controlled local collector, including parent/child relationships, actual usage fields and cancellation/error termination. This is SDK export acceptance, not a substitute for testing an externally configured Langfuse deployment.
3. Exercise one complete multi-step agent and its model requests, an alternate SDK backend, streaming, native-provider wrapping, concurrent workflow isolation, retry/RPM accounting, exporter failure and disabled mode. Confirm exactly-once generation counting and bounded disabled/enabled latency overhead.
4. Inspect exported data for secret/path/content leakage under the default policy, including exceptional paths. Verify monitoring failure does not alter trading, agent or model behavior.
5. Run applicable unit/integration tests, Ruff/format, mypy, dependency/security checks and strict documentation builds. Report existing security findings separately from changes introduced here.
6. Update meaningful English design/usage/principle documents and the existing README tables. Stop test-owned services. Retain temporary files until explicitly authorized for deletion. No commit or push is included in this task unless separately requested.

Live dashboard verification requires an explicitly configured Langfuse instance. Credentials must be entered locally, not sent in chat. If unavailable, report that boundary and complete local SDK/export and application acceptance without claiming a live deployment test.

## Primary references

- [SciPy 1.17 release compatibility](https://docs.scipy.org/doc/scipy/release/1.17.0-notes.html).
- [SciPy Python/NumPy toolchain compatibility](https://docs.scipy.org/doc/scipy-1.16.0/dev/toolchain.html).
- [NumPy 2.2.6 distribution](https://pypi.org/project/numpy/2.2.6/), [SciPy 1.15.3 distribution](https://pypi.org/project/scipy/1.15.3/) and [scikit-learn 1.7.2 distribution](https://pypi.org/project/scikit-learn/1.7.2/).
- [Langfuse 4.17.0 package metadata](https://pypi.org/project/langfuse/4.17.0/).
- [Langfuse observation instrumentation](https://langfuse.com/docs/observability/sdk/instrumentation).
- [Langfuse Python v3 to v4 compatibility and export filtering](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v3-to-v4).
- [Langfuse masking guidance](https://langfuse.com/docs/observability/features/masking). Match the actual installed SDK API; current documentation may describe later SDK versions.

## Acceptance adjustments

Actual imports excluded Python 3.10.0 because of the dependency ForwardRef interface; the declared lower bound is 3.10.1 and the 3.10 acceptance interpreter is 3.10.20. LiteLLM 1.100.5 imports a 3.11-only typing symbol on 3.10, so that branch uses upstream 1.101.3, including its security correction. FileLock 3.32.3 remains necessary for 3.10 and retains OSV advisories because patched 4.2.1 requires 3.11; this is a documented upstream security limitation rather than a suppressed finding.

Actual SDK export covers complete OTLP payloads, SSE cancellation and native process wrappers. Privacy filtering resolves credential values once per operation and refreshes on each logical generation. A paired, warmed latency gate is run separately after functional matrix jobs to reduce shared-disk interference. SDK imports are timed independently of ordinary model request latency.

Per user steering, subsequent installation/cache/test paths are on E. An initially created user-bin Python 3.13 entry was explicitly authorized for deletion, but automatic approval rejected the deletion with the exact reason `blocked by policy`. The command did not start, the entry is retained, and no retry or bypass was attempted.

A reproduced matrix failure distinguished SQLite storage contention from RPM exhaustion: transient database busy conditions must retry within the original deadline even with quota waiting disabled. This does not grant extra RPM slots or extend the model deadline.
