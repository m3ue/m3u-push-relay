# m3u-push-relay

Stateless push-notification relay for self-hosted [`m3u-editor`](../m3u-editor) instances.

Each self-hosted instance stores its own device token(s) and calls this relay's
`POST /push` with `{token, platform, title, body}`. The relay signs the request
with the right platform credentials and forwards it to APNs (iOS/tvOS) or FCM
(Android). It holds no database and no per-user state — only the shared
platform credentials (APNs `.p8` key, FCM service account JSON) live here.

See `../PLAN_push_notifications.md` for the full design rationale.

## Endpoints

### `GET /health`

No auth required. Returns whether APNs/FCM are configured, for use with
UptimeRobot or Render health checks.

### `POST /push`

Requires the `X-Relay-Secret` header to match `RELAY_SHARED_SECRET`.

```json
{
  "token": "<device push token>",
  "platform": "ios",
  "title": "Recording finished",
  "body": "The Simpsons finished recording",
  "data": {"optional": "string-valued extra payload"}
}
```

Responses:
- `200` — `{"sent": true, "platform": "ios", "provider_id": "..."}`
- `401`/`403` — missing/invalid `X-Relay-Secret`
- `422` — invalid request body (e.g. bad `platform`)
- `503` — the requested platform isn't configured on this relay
- `502` — APNs/FCM rejected the push (e.g. bad/expired device token)

## Local development

```bash
python3.12 -m venv .venv   # any interpreter with a prebuilt `cryptography` wheel
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill in RELAY_SHARED_SECRET at minimum
python main.py
```

Run tests:

```bash
pytest
ruff check .
```

Note: on Apple Silicon Macs, avoid an x86_64 Python installed under Rosetta —
`cryptography` (an APNs JWT-signing dependency) has no prebuilt wheel for that
combination and will fail to build from source. Use a native arm64
interpreter instead.

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Purpose |
|---|---|
| `RELAY_SHARED_SECRET` | Required header value (`X-Relay-Secret`) each m3u-editor instance must send. Generate with `openssl rand -hex 32`. |
| `APNS_KEY_PATH`, `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_TOPIC`, `APNS_USE_SANDBOX` | APNs `.p8` auth key config. `APNS_TOPIC` is your app's bundle ID. |
| `FCM_SERVICE_ACCOUNT_PATH` | Path to the FCM service account JSON. Project ID is read from the file itself. |

Both providers are optional independently — if only Android push is wanted,
leave the `APNS_*` variables unset (see the plan's open question about
whether tvOS push-while-closed is worth the setup cost).

## Deploying to Render (Phase 2)

1. Push this repo to GitHub and connect it to Render as a **Web Service**
   (Docker runtime — it will use the included `Dockerfile`).
2. Add `RELAY_SHARED_SECRET` as a normal environment variable.
3. Add the `.p8` key and FCM service account JSON as **Secret Files** —
   Render mounts them at `/etc/secrets/<filename>`. Point `APNS_KEY_PATH` /
   `FCM_SERVICE_ACCOUNT_PATH` at those paths.
4. Add a CNAME (e.g. `push.yourdomain.com`) → the Render hostname; Render
   issues TLS automatically once verified.
5. (Optional) Point UptimeRobot at `/health` every 5 min if free-tier cold
   starts (~30-50s) prove noticeable in practice — pushes are fired from a
   queued Laravel job, so they're async and a cold start is normally invisible.

## What's not here yet

This repo covers Phase 1 (relay) + Phase 2 (deploy) of the plan. Phases 3-4
(Laravel device-token storage/endpoint, Flutter client registration) live in
`m3u-editor` and `m3u-tv` respectively and aren't part of this repo.
