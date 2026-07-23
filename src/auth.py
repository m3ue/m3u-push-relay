import hmac

from fastapi import Header, HTTPException

from config import settings


async def verify_shared_secret(x_relay_secret: str | None = Header(default=None)) -> None:
    """Require a matching X-Relay-Secret header on every /push call.

    Mirrors m3u-proxy's API_TOKEN convention: unset RELAY_SHARED_SECRET disables
    auth entirely (local testing only — always set it in production).
    """
    if not settings.RELAY_SHARED_SECRET:
        return

    if x_relay_secret is None:
        raise HTTPException(status_code=401, detail="Relay secret required")

    if not hmac.compare_digest(x_relay_secret, settings.RELAY_SHARED_SECRET):
        raise HTTPException(status_code=403, detail="Invalid relay secret")
