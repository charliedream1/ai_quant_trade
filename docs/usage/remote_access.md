# Remote access from chat and a browser

The administration module's Help page contains an expanded **远程接入说明** panel. It explains both chat-bot access and browser access. Reading it does not inspect credentials, enable a channel, contact a provider or start a service.

## Connect a chat account

Open System configuration → Messaging channels. Configure Feishu's `FEISHU_APP_ID` and `FEISHU_APP_SECRET`, or WeCom's `WECOM_BOT_ID` and `WECOM_BOT_SECRET`, in local `.env` or `.llm_env`. For WeChat, request a QR code, scan it in the eligible account and check the login result. Never paste credentials into a shared chat or commit environment files.

Enable the selected channel and the gateway. Long-connection adapters initiate outbound connections; they do not need another public inbound webhook. Keep the platform or standalone gateway running while using a remote client.

Send a private message to the bot to receive a short-lived pairing code. Refresh management, verify the binding ID, sender and conversation, then enter that private code locally. Grant the exact operations, named knowledge libraries, templates and push subscriptions needed by that account. Empty resource lists do not mean unrestricted access.

Send `/help` and `/status` first. A workflow command returns a preview; execute it only by sending the associated `/confirm` code. Use the explicit test-message action for a binding with push permission and verify actual receipt in the chat. Provider acceptance and receipt are different states.

Revoking a binding blocks new operations and delivery. A later private message can request fresh pairing, but cannot restore permission by itself. WeChat context and account authorization can expire; a new message or QR login may be required. Closing the browser does not stop background services.

## Connect through a browser

Use the existing platform access boundary documented in [Access control](access_and_execution.md). Configure `ALL_IN_ONE_ACCESS_MODE=token`, a strong `ALL_IN_ONE_ACCESS_TOKEN` of at least 32 ASCII characters, and `ALL_IN_ONE_ACCESS_HOSTS` containing the real access hostname. Wildcard host access is not allowed.

If another device must reach the service, explicitly set the listening host through `ALL_IN_ONE_HOST`. Use a trusted HTTPS reverse proxy and preserve WebSocket upgrades and SSE streaming. Preserve the platform's same-origin routing. Do not disable access validation or expose an anonymous instance to work around connectivity problems.

Restart after deployment changes. Open the configured HTTPS workspace URL on the phone or remote computer and authenticate with the locally configured access token. Verify health, login, a read-only query and channel state before starting a long task. Keep private hostnames, tokens, certificates and account settings out of Git.

## Troubleshooting

| Observation | Check |
| --- | --- |
| Configured but not online | Optional channel dependencies, app publication, receive/send permissions and gateway status. |
| A pairing code appears | Approve that exact private sender/conversation locally, then send the message again. |
| A command is denied | Binding grants, resource names, confirmation expiry and changed template revisions. |
| WeChat is waiting for context | Send a fresh private message; use QR login again if authorization expired. |
| Remote browser is rejected | Actual hostname allowlist, token mode, HTTPS and trusted proxy configuration. |

The application ships no public service address or account credentials. Local protocol simulations do not establish that a real account has been connected.
