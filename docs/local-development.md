# Local development runbook

This runbook exists because local environment failures can otherwise masquerade as product, model, Azure, browser or orchestration failures. The rule is simple:

> Credential expiry is the first hypothesis, not the last discovery.

## Start-of-day ritual

Use this at the start of each development session:

```bash
cd /Users/martin/Documents/Codex/2026-07-06/le/dctwin
source .venv/bin/activate
PYTHONPATH=src .venv/bin/python -m dctwin.dev --reset --refresh-auth
```

This:

- loads local `.env` configuration;
- runs the local environment ping;
- clears disposable session/cache state;
- forces the Azure credential handshake before the server accepts CV ingestion work;
- prints the Azure device-code flow if sign-in is required;
- prints the acquired token expiry time;
- starts the local preview server on `127.0.0.1:8766`.

Open:

```text
http://127.0.0.1:8766/api/health
```

Expected healthy shape:

```json
{
  "status": "ok",
  "foundry": "ready",
  "azure_auth": ["device_code"],
  "azure_tenant": "configured",
  "auth_mode": "device_code",
  "model_path": "staged_extraction"
}
```

## Local configuration

Local Foundry configuration lives in ignored `.env`.

Required:

```bash
FOUNDRY_PROJECT_ENDPOINT=...
DCTWIN_MODEL_DEPLOYMENT=...
AZURE_TENANT_ID=...
DCTWIN_MODEL_PATH=staged_extraction
DCTWIN_AUTH_MODE=device_code
DCTWIN_AUTH_TIMEOUT_SECONDS=180
```

Notes:

- `AZURE_TENANT_ID` must be only the tenant value itself.
- Do not paste labels such as `Tenant ID:`.
- Do not put comments on the same line as a value.
- Azure Identity accepts letters, numbers, hyphens and dots for tenant identifiers.
- `DCTWIN_AUTH_MODE=device_code` is preferred locally because it keeps the Azure handshake visible in the terminal and prevents the app browser from being redirected away from DCT.

## Ping commands

Use ordinary ping for non-invasive readiness:

```bash
PYTHONPATH=src .venv/bin/python -m dctwin.ping
```

Use auth ping when Foundry calls appear slow, stuck or suspicious:

```bash
PYTHONPATH=src .venv/bin/python -m dctwin.ping --auth
```

`ping --auth` actively acquires an Azure token, shows any required device-code login, and reports the token expiry time. This should be the first troubleshooting move for any Foundry-backed ingestion failure.

## Ockham order for local failures

When CV ingestion hangs or fails, check in this order:

1. Expired or missing Azure credential.
2. Missing or malformed `.env` values.
3. Wrong tenant or account context.
4. Local server not running or stale.
5. Port conflict.
6. Python virtual environment/import failure.
7. Azure quota/deployment/model issue.
8. Actual Source Adapter/model/reconciliation bug.

Do not start with prompt tuning, model behavior or schema debugging until auth/config has been ruled out.

## Observability during ingestion

Live progress is written to:

```bash
.dctwin-local/logs/ingestion-progress.jsonl
```

Watch it with:

```bash
tail -f .dctwin-local/logs/ingestion-progress.jsonl
```

Important events:

- `upload_received`
- `system_health_checked`
- `text_extraction_started`
- `text_extraction_completed`
- `model_provider_initializing`
- `azure_token_acquisition_started`
- `azure_device_code_prompted`
- `azure_token_acquisition_completed`
- `model_call_started`
- `model_call_completed`
- `reconciliation_started`
- `reconciliation_completed`
- `mirror_rendered`

If the last event is `azure_device_code_prompted`, the system is waiting for the Azure sign-in code to be completed. This is not a model hang.

## UI rule

External service handshakes are user-visible workflow states.

If Azure requires device-code sign-in, the UI must surface the sign-in URL, code and expiry rather than remaining on a generic “rendering” or “constructing” step.

This follows ADR-018: external service handshakes are first-class workflow states.

## What is disposable

Safe to reset for local development:

```bash
.dctwin-local/
```

This contains the local Session Twin, cache and ingestion logs.

Do not casually delete:

```bash
~/.dctwin/
```

This contains local persistent account/Twin state.
