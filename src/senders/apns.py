import time
from typing import Dict, Optional

import httpx
import jwt

from models import PushSendError

# Apple accepts provider tokens up to 60 minutes old; refresh well before that
# so a slow request never straddles the boundary.
_TOKEN_TTL_SECONDS = 45 * 60

_PRODUCTION_HOST = "https://api.push.apple.com"
_SANDBOX_HOST = "https://api.sandbox.push.apple.com"


class APNsSender:
    """Sends alerts via APNs HTTP/2, authenticating with a .p8 auth key (JWT).

    Stateless per relay instance: the signed provider token is cached in memory
    and reused across requests until it nears expiry, per Apple's guidance.
    """

    def __init__(self, key_path: str, key_id: str, team_id: str, topic: str, use_sandbox: bool = False):
        self.key_id = key_id
        self.team_id = team_id
        self.topic = topic
        self.host = _SANDBOX_HOST if use_sandbox else _PRODUCTION_HOST

        with open(key_path, "r") as f:
            self._private_key = f.read()

        self._cached_token: Optional[str] = None
        self._cached_token_at: float = 0.0

    def _provider_token(self) -> str:
        now = time.time()
        if self._cached_token and (now - self._cached_token_at) < _TOKEN_TTL_SECONDS:
            return self._cached_token

        token = jwt.encode(
            {"iss": self.team_id, "iat": int(now)},
            self._private_key,
            algorithm="ES256",
            headers={"kid": self.key_id},
        )
        self._cached_token = token
        self._cached_token_at = now
        return token

    async def send(self, device_token: str, title: str, body: str, data: Optional[Dict[str, str]] = None) -> str:
        payload = {
            "aps": {
                "alert": {"title": title, "body": body},
                "sound": "default",
            },
            **(data or {}),
        }
        headers = {
            "authorization": f"bearer {self._provider_token()}",
            "apns-topic": self.topic,
            "apns-push-type": "alert",
            "apns-priority": "10",
        }

        async with httpx.AsyncClient(http2=True, timeout=10.0) as client:
            response = await client.post(
                f"{self.host}/3/device/{device_token}",
                json=payload,
                headers=headers,
            )

        if response.status_code == 200:
            return response.headers.get("apns-id", "")

        try:
            reason = response.json().get("reason", response.text)
        except ValueError:
            reason = response.text
        raise PushSendError(f"APNs rejected push: {reason}", status_code=502)
