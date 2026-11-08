# Messaging Channels and Remote Platform Control

Date: 2026-11-06. Author: Codex. Status: approved and implemented; real-account acceptance remains environment-dependent.

## Objective and scope

Connect the quant platform to Feishu/Lark, personal WeChat through the iLink bot protocol, and WeCom AI Bots. Users can bind a permitted conversation, subscribe to recorded platform events, ask questions, and operate explicitly authorized platform workflows. This design contains no implementation code.

The first release covers text messages, notification summaries, report identifiers, connection management, and a bounded command set. Voice, OCR, arbitrary attachment execution, desktop automation, live order placement, arbitrary shell commands, and general filesystem access are outside this release. Additional channels can implement the same adapter contract later.

## Existing behavior and reuse

The repository already has persistent notifications, real task services, API access control, and cross-process task ownership. These remain the sources of truth.

| Existing location | Behavior to preserve or extend |
| --- | --- |
| `src/notifications/service.py:NotificationService.feed` | Source synchronization currently depends primarily on an inbox read and an in-process interval cache. External delivery must continue without an open browser. |
| `src/notifications/store.py:NotificationStore.publish` | Persists deduplicated source events. Extend delivery after successful persistence; network failure must not roll back the originating task. |
| `src/notifications/sources.py:synchronize/task` | Reads bounded, recorded factor, system, backtest, scheduler, and research results. Preserve source status and avoid new market or model requests for notification discovery. |
| `src/scheduler/executor.py:SchedulerService.trigger/enable` | Reuse recorded executions, concurrency control, deadlines, retries, and real job status. Restrict remotely runnable job types and existing saved identifiers. |
| `src/engine/backtest/jobs.py:submit/cancel` | Reuse asynchronous submission and cooperative cancellation rather than introduce a separate simulation runner. |
| `src/core/task_control.py:TaskLease/TaskEvent` | Reuse shared SQLite ownership and cancellation. A cancellation request does not mean the worker has already stopped. |
| `src/api/security.py:AccessControl` | Protect channel management through the existing administrator boundary. A browser client identifier is not an authorized channel identity. |
| `src/agent/llm_client.py` and `src/observability/` | Preserve configured HTTP/OpenAI/LiteLLM providers, shared RPM controls, and optional privacy-filtered Langfuse observations. |

The current repository has substantial earlier uncommitted work. Development must preserve that work and isolate this feature's changes. No commit or push is part of this proposal.

## Reference investigation

Upstream nanobot was inspected at revision `475b045b6f7c337f276c251f96401f68386579b1`. Relevant references include its channel adapters, normalized message bus, connection lifecycle, pairing store, and outbound notification policy. The inspected current nanobot README requires Python 3.11 or newer, so importing its complete runtime would narrow this platform's supported Python range. Implement a small native integration using compatible optional dependencies instead.

The local GenericAgent checkout was inspected at revision `f308ee7eb079cc402edf5a934fa65f6d71a4c7ad`. Its `frontends/wechatapp.py`, `frontends/fsapp.py`, and `frontends/wecomapp.py` provide additional protocol examples. Do not import these frontend scripts: they include startup side effects, user-home state, global process changes, and unrestricted agent capabilities that do not fit this platform. Preserve required upstream attribution if implementation code is adapted.

A local ms-agent checkout at revision `f491aaaee84dc1ba3bb3cbfaf3258fefe9ff2dc7` contains `examples/nanobot_integration`. It demonstrates MCP capability exposure, rather than a transport implementation, and is not needed for the first release. No local reference checkout was modified or executed.

## Transport choices and delivery limits

| Channel | Connection and binding | Outbound behavior |
| --- | --- | --- |
| Feishu/Lark | Official Python SDK WebSocket subscription; configured application credentials; administrator approves the exact sender and conversation. | Send text or bounded formatted summaries using the platform API and configured bot permissions. No public inbound webhook is required for this mode. |
| WeChat | QR login and HTTP long polling following Tencent's iLink protocol; local approval of the sender; direct conversations first. | Send using valid account and conversation context. Context restrictions, exhausted message budget, expired login, and upstream failures must remain visible. This is not unrestricted delivery to arbitrary WeChat contacts. |
| WeCom | AI Bot long connection; configured Bot ID and Secret; sender/conversation approval. | Send permitted text or Markdown notifications within the bot's platform restrictions. Enterprise application callbacks and broad department/contact messaging are separate future work. |

WeChat's context lifetime and available send quota are not stable guarantees. Upstream implementations and issues show context-related send failures, but differing observed lifetimes do not justify a fixed universal expiration claim. Treat the actual response and current session state as authoritative. A success response is upstream acceptance, not proof that a person read the message. When context is unavailable, retain a bounded pending item until new context or expiry, and offer other independently subscribed channels; never silently broadcast private content to another destination.

Each adapter normalizes verified channel instance, sender, conversation, provider message identifier, text, timestamp, and transport-specific reply context. Only validated text reaches the command router. Group operation, where supported, requires an explicitly approved group, permitted sender, and bot mention. WeChat group support is not assumed.

## Binding and administration

Add a dedicated channel-management panel under system configuration. Show configured, connecting, online, reconnecting, authorization required, and degraded states separately. A saved credential is not evidence of a working connection.

Support enable/disable, WeChat QR login and expiry, sender pairing requests, approval/revocation, destination selection, subscription filters, command permissions, safe connection diagnostics, and a deliberately labeled test-message action. Binding approval and permission changes require the existing local/administrator control boundary; a remote chat cannot approve itself or grant capabilities to another chat.

Pairing codes are random, short-lived, attempt-limited, stored as hashes, and bound to the exact channel instance, sender, and conversation. An empty allowlist grants no access. Keep separate grants for queries, model requests, template execution, cancellation, and scheduler changes. The gateway must not forward a new sender's text to a model before authorization.

Revocation immediately blocks new commands and delivery to that binding and invalidates its outstanding confirmations. Revocation does not silently cancel an already running task. Persist destination identities and grant records only as private runtime data, never as checked-in examples or logs intended for publication.

## Remote actions

| Operation | Initial contract |
| --- | --- |
| Help and status | Show permitted operations, gateway health, authorized task states, and safe system summaries without secrets or local paths. |
| Task and report lookup | Return only permitted identifiers, status, metrics, and bounded summaries. Do not expose raw filesystem paths or generate unprotected download links. |
| Knowledge and assistant questions | Use the existing model configuration and explicitly permitted knowledge libraries. Maintain conversations by channel instance, sender, and conversation; group context cannot expose a private conversation. |
| Run a workflow | Execute an administrator-approved saved backtest, research, or scheduler template. Validate referenced resources and saved parameters at execution time; arbitrary scripts, raw job payloads, and unapproved job types are rejected. |
| Cancel a task | Allow only a task created under the same binding's authorized request, or a task explicitly granted by the administrator. Report requested, stopping, and stopped truthfully. |
| Enable or disable a schedule | Optional permission for an approved existing schedule. Require a preview and one-time confirmation before the change. Creating or deleting schedules through chat is outside this release. |

Deterministic commands remain available without an LLM. Natural-language questions use ordinary generation; any model-produced intent is parsed with `json_repair` and validated against the same command and resource allowlists. A model cannot grant permissions, infer confirmation from conversation history, or turn retrieved content into an executable instruction. Preserve traditional ReAct behavior for allowed tools and existing model RPM accounting.

State-changing actions show the exact action, saved template or task, and relevant parameters before execution. A one-time confirmation is scoped to the binding, canonical action digest, resource revision, and expiry. Consuming it is atomic and cannot authorize an edited template, replayed message, or different conversation. Query operations do not need this extra confirmation.

Long work returns a request/task identifier immediately. Completion, failure, and cooperative cancellation are delivered asynchronously from persisted actual outcomes. A duplicate inbound provider message must not create another run. Persist intent acceptance before dispatch; reconcile restart gaps against recorded task identifiers. An uncertain submission is marked for review rather than automatically executing a second time.

## Notification delivery and runtime

Use a bounded durable SQLite outbox with independent delivery records for each event and authorized destination. Creation is idempotent for the event, subscription, and destination. Store only the bounded message needed for delivery, with privacy filtering before transport and logging. Resolve bindings again before sending so revocation takes effect on queued items.

Prefer lightweight event publication after task state commits, plus incremental background reconciliation for missed events and other processes. Use persistent source cursors and bounded catch-up pages; do not rely only on the most recent fixed-size window. On first binding, begin from an explicit current watermark unless an administrator requests a bounded historical catch-up. Merely opening a browser must not resend historical notifications.

One elected gateway owns each configured channel instance through a renewable cross-process lease. API workers and an optional standalone gateway entrypoint may share the runtime database, but may not open duplicate WeChat pollers or duplicate long connections. Lease loss stops inbound consumption and outbound dispatch before reacquisition. Channel failure does not stop the Web/API service or affect a trading task's state.

Keep reconnection, inbound queue size, message length, provider API rate limits, outbox retention, deadlines, retry count, and batching in YAML. Secrets and account authentication tokens belong only in local `.env` or `.llm_env`, with placeholders in the sample. QR completion writes tokens through a narrowly validated local environment update; polling cursors and sensitive conversation context use a separately ignored private state store. Credentials and reply context must never appear in model prompts, Langfuse content, browser diagnostics, or committed files.

All installations, caches, QR artifacts, and test temporary files use explicitly configured locations on the E drive in this development session. Do not fall back to the user profile, C-drive temporary directories, or global package installation. Production defaults remain portable and project-relative/configurable rather than containing developer-specific absolute paths.

Retry safe reads and definite non-delivery responses with capped exponential backoff and jitter. Respect provider retry timing. For a timed-out send whose acceptance is unknown, record an ambiguous outcome; use a documented provider idempotency mechanism if available, otherwise do not blindly retry. Delivery is not advertised as exactly once across a network failure. WeChat context and authentication failures require the appropriate refresh or reauthorization rather than repeated failing sends.

Report queue depth, oldest pending age, last confirmed transport success, current failure category, and lease ownership safely. Use bounded Loguru records and optional Langfuse spans for authorized agent/model actions. Stop pollers, connections, retry loops, and owned worker queues within a configured shutdown budget.

## Planned implementation boundaries

| Location | Intended change |
| --- | --- |
| `src/channels/` | Small adapter contracts, configuration, bindings, gateway lifecycle, durable delivery, command authorization, and channel-specific transports in separate modules. |
| `src/notifications/` and existing terminal task hooks | Reuse stored events and add minimal background publication/reconciliation interfaces. Preserve current inbox behavior. |
| `src/api/routes/` and application lifespan | Protected channel status, binding, login, subscription, and management operations; bounded runtime start/stop. |
| `src/frontend/features/` and related handlers/services | A separate messaging configuration panel with safe state, pairing, subscriptions, diagnostics, and command grants. |
| `egs/` and `.env.example` | YAML transport/command policy, standalone gateway entry, optional dependency profile, and empty environment placeholders. |
| `tests/channels/` and existing regression categories | Protocol, authorization, task, delivery, lifecycle, browser, privacy, and compatibility acceptance. |
| Public docs and navigation | English usage/principle documents, relevant API/schema design updates, existing README update tables, and a concise dated changelog. |

Do not modify the full agent execution engine, trading rules, or model provider interface for transport support. Optional messaging dependencies must be pinned to versions actually tested on the supported Python series; do not narrow Python support just to install the full reference project.

## Acceptance and remaining external requirements

Unit checks cover pairing, expiry, revocation, ownership, group rules, canonical confirmations, message replay, input bounds, redaction, and parsing. Integration checks use real existing task services and local protocol endpoints to verify connection recovery, provider business failures, bounded queues, durable restart/catch-up, cross-process leadership, cancellation, notification source agreement, and ambiguous-send handling. Concurrent duplicate messages and a crash between acceptance and submission must not silently create duplicate work.

Measure publication-to-outbox and local-protocol delivery latency independently of model, backtest, network, and provider time. Use a provisional local acceptance target of p95 below two seconds for a newly committed event reaching an available adapter under the documented test workload. Measure discovery latency separately for reconciliation-only sources and compare enabled/disabled request and task overhead. Do not present this target as an external delivery SLA.

Validate binding and permission flows in the actual browser; run applicable unit/integration regression, Ruff, mypy, dependency consistency, pip-audit, Gitleaks, OSV, UTF-8/privacy checks, and both strict documentation builds. Exercise optional imports and adapter construction on Python 3.10 through 3.14, with Windows/Linux coverage clearly distinguished from CI definitions. Record pre-existing dependency advisories separately. Stop all test-owned services. Retain temporary files unless deletion is explicitly approved.

Real-account acceptance additionally requires the user's WeChat QR scan and eligible account, Feishu app permissions and local credentials, and WeCom Bot ID/Secret and enabled long-connection capability. Obtain these through local configuration, not chat messages or checked-in files. Offline protocol acceptance cannot establish successful delivery to those accounts. Once configured, send a single explicitly requested test message and verify receipt before claiming that real binding and push are operational.

## Primary sources

- [nanobot channel implementation at the inspected revision](https://github.com/HKUDS/nanobot/tree/475b045b6f7c337f276c251f96401f68386579b1/nanobot/channels): transport separation, connection management, WeChat context handling, and Feishu/WeCom adapters.
- [nanobot WeChat setup guide](https://github.com/HKUDS/nanobot/blob/475b045b6f7c337f276c251f96401f68386579b1/docs/guides/wechat-ai-agent.md): QR login, HTTP polling, sender pairing, and runtime requirements.
- [nanobot Feishu setup guide](https://github.com/HKUDS/nanobot/blob/475b045b6f7c337f276c251f96401f68386579b1/docs/guides/feishu-ai-agent.md): application setup, long connections, sender approval, and permission diagnostics.
- [Tencent iLink protocol reference](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md): authentication, QR flow, polling, send requests, and operation-specific response handling.
- [Tencent context-related delivery issue](https://github.com/Tencent/openclaw-weixin/issues/286): observed context restrictions; not a guaranteed account-independent lifetime.
- [Feishu long-connection documentation](https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-subscription-configure-): SDK authentication and event reception.
- [Official Feishu Python SDK](https://github.com/larksuite/oapi-sdk-python): implementation and release metadata for the optional client dependency.
- [WeCom team's integration](https://github.com/WecomTeam/wecom-openclaw-plugin): AI Bot long connections, delivery modes, and platform-side prerequisites.
- [GenericAgent](https://github.com/lsdefine/GenericAgent/tree/f308ee7eb079cc402edf5a934fa65f6d71a4c7ad/frontends): additional protocol examples from the locally available reference, subject to its MIT license.

## Investigation outcome

The requested channels are feasible without replacing the platform runtime. The approved implementation adds native adapters, authorization, durable delivery and bounded remote actions. No channel credentials were requested or read, and no real account message was sent. Real-account connection and receipt remain environment-dependent acceptance steps.
