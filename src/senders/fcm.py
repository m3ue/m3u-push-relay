import asyncio
import json
from typing import Dict, Optional

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from models import PushSendError

_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


class FCMSender:
    """Sends notifications via the FCM HTTP v1 API, authenticating with a
    Firebase service account JSON key.

    Handles both Android and iOS: Apple delivery works because the APNs auth
    key (.p8) is uploaded directly to the Firebase console for the iOS app,
    so FCM bridges to APNs itself — this relay never touches APNs directly
    or holds Apple credentials.
    """

    def __init__(self, service_account_path: str):
        self._credentials = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=_SCOPES
        )
        with open(service_account_path, "r") as f:
            self.project_id = json.load(f)["project_id"]

    def _access_token(self) -> str:
        # Credentials.refresh() is a blocking network call; callers run this
        # via asyncio.to_thread so it doesn't block the event loop.
        if not self._credentials.valid:
            self._credentials.refresh(GoogleAuthRequest())
        return self._credentials.token

    async def send(
        self,
        device_token: str,
        title: str,
        body: str,
        platform: Optional[str] = None,
        data: Optional[Dict[str, str]] = None,
    ) -> str:
        access_token = await asyncio.to_thread(self._access_token)

        message = {
            "token": device_token,
            "notification": {"title": title, "body": body},
            "data": data or {},
        }
        if platform == "ios":
            message["apns"] = {"payload": {"aps": {"sound": "default"}}}
        elif platform == "android":
            message["android"] = {"priority": "high"}

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send",
                json={"message": message},
                headers=headers,
            )

        if response.status_code == 200:
            return response.json().get("name", "")

        try:
            reason = response.json().get("error", {}).get("message", response.text)
        except ValueError:
            reason = response.text
        raise PushSendError(f"FCM rejected push: {reason}", status_code=502)
