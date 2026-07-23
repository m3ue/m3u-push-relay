# m3u-push-relay

Stateless push-notification relay for self-hosted [`m3u-editor`](../m3u-editor) instances.

**Mobile only** (phone/tablet builds of `m3u-tv`) — TV builds (Android TV,
tvOS) don't use push.

Each self-hosted instance stores its own device token(s) and calls this relay's
`POST /push` with `{token, platform, title, body}`. The relay forwards it to
Firebase Cloud Messaging (FCM), which delivers to Android natively and bridges
to APNs for iOS. It holds no database and no per-user state — only the shared
Firebase service account credential lives here.

**Why FCM for both platforms, not direct APNs**: Android push requires FCM —
there's no way around that, Google retired the legacy alternative years ago.
Since a Firebase project is mandatory anyway, we upload the APNs `.p8` auth
key directly into the Firebase console (Project Settings → Cloud Messaging →
Apple app configuration) and let Firebase handle Apple delivery too. This
relay never touches Apple credentials directly — it only ever holds one
Firebase service account JSON, for both platforms. (Simpler, and it also
means no JWT-signing/`cryptography`-build headaches on this side.)

## Endpoints

### `GET /health`

No auth required. Returns whether FCM is configured, for use with UptimeRobot
or Render health checks.

### `POST /push`

Requires the `X-Relay-Secret` header to match `RELAY_SHARED_SECRET`.

```json
{
  "token": "<device FCM registration token>",
  "platform": "ios",
  "title": "Recording finished",
  "body": "The Simpsons finished recording",
  "data": {"optional": "string-valued extra payload"}
}
```

`platform` (`ios` | `android`) only affects minor delivery hints (APNs sound,
Android priority) — both platforms are sent through the same FCM call.

Responses:
- `200` — `{"sent": true, "platform": "ios", "provider_id": "..."}`
- `401`/`403` — missing/invalid `X-Relay-Secret`
- `422` — invalid request body (e.g. bad `platform`)
- `503` — FCM isn't configured on this relay
- `502` — FCM rejected the push (e.g. bad/expired device token)

## Local development

```bash
python3.12 -m venv .venv
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

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Purpose |
|---|---|
| `RELAY_SHARED_SECRET` | Required header value (`X-Relay-Secret`) each m3u-editor instance must send. Generate with `openssl rand -hex 32`. |
| `FCM_SERVICE_ACCOUNT_PATH` | Path to the Firebase service account JSON. Project ID is read from the file itself. |

## Firebase project setup

One Firebase project covers both the Android and iOS mobile apps:

1. **Create the project**: [Firebase Console](https://console.firebase.google.com) → Add project.
2. **Add the Android app** — package name `dev.sparkison.tv` (from `m3u-tv/flutter_client/android/app/build.gradle.kts`). Download `google-services.json` (goes in the Flutter project, not here).
3. **Add the iOS app** — bundle ID `dev.sparkison.tv` (from `m3u-tv/flutter_client/ios/Runner.xcodeproj`). Download `GoogleService-Info.plist` (goes in the Flutter project, not here).
4. **Upload the APNs auth key** — Project Settings → Cloud Messaging → Apple app configuration → APNs Authentication Key. Upload the `.p8` file plus its Key ID and your Apple Team ID. One-time; Firebase re-signs its own JWTs to APNs from then on. This step is what lets FCM deliver to the iOS app at all — without it, iOS sends will fail even though Android works.
5. **Generate the relay's credential** — Project Settings → Service Accounts → Generate new private key. This is the *only* secret this relay needs (`FCM_SERVICE_ACCOUNT_PATH`).

None of the above ever needs to reach end users — it's split as:
- `google-services.json` / `GoogleService-Info.plist` → bundled into the Flutter app builds (not secret, but keep out of a public repo anyway — see `m3u-tv` notes).
- Service account JSON + APNs `.p8` key → stay in the Firebase console and this relay's Render Secret Files, never in a client build or a repo.

## Deploying to Render (Phase 2)

1. Push this repo to GitHub and connect it to Render as a **Web Service**
   (Docker runtime — it will use the included `Dockerfile`).
2. Add `RELAY_SHARED_SECRET` as a normal environment variable.
3. Add the Firebase service account JSON as a **Secret File** — Render mounts
   it at `/etc/secrets/<filename>`. Point `FCM_SERVICE_ACCOUNT_PATH` at that path.
4. Add a CNAME (e.g. `push.yourdomain.com`) → the Render hostname; Render
   issues TLS automatically once verified.
5. (Optional) Point UptimeRobot at `/health` every 5 min if free-tier cold
   starts (~30-50s) prove noticeable in practice — pushes are fired from a
   queued Laravel job, so they're async and a cold start is normally invisible.

## What's not here yet

This repo covers Phase 1 (relay) + Phase 2 (deploy) of the plan. Phases 3-4
(Laravel device-token storage/endpoint, Flutter client registration) live in
`m3u-editor` and `m3u-tv` respectively and aren't part of this repo.
