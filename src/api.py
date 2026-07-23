import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from config import VERSION, settings
from models import PushRequest, PushResponse, PushSendError
from rate_limit import RateLimiter
from senders.fcm import FCMSender

logger = logging.getLogger(__name__)

ip_rate_limiter = RateLimiter(max_events=settings.RATE_LIMIT_PER_IP_PER_MINUTE, window_seconds=60)
token_rate_limiter = RateLimiter(max_events=settings.RATE_LIMIT_PER_TOKEN_PER_HOUR, window_seconds=3600)


def _client_ip(request: Request) -> str:
    # Render/Cloudflare sit in front of this service - the direct peer is
    # always the proxy, so prefer the original client from X-Forwarded-For.
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _build_fcm_sender() -> FCMSender | None:
    if not settings.fcm_configured:
        logger.warning("FCM not configured — push requests will fail")
        return None
    return FCMSender(service_account_path=settings.FCM_SERVICE_ACCOUNT_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.fcm_sender = _build_fcm_sender()
    yield


app = FastAPI(
    title="m3u-push-relay",
    version=VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    openapi_url=settings.OPENAPI_URL,
    lifespan=lifespan,
)


@app.get("/")
async def root():
    # Render's health check path defaults to "/" — this avoids a 404 there
    # causing Render to think the service is unhealthy and cycle it.
    return {"status": "healthy", "version": VERSION}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": VERSION,
        "fcm_configured": settings.fcm_configured,
    }


@app.post("/push", response_model=PushResponse)
async def push(request: PushRequest, http_request: Request):
    if not ip_rate_limiter.allow(_client_ip(http_request)):
        raise HTTPException(status_code=429, detail="Too many requests from this source — try again shortly")

    if not token_rate_limiter.allow(request.token):
        raise HTTPException(status_code=429, detail="Too many pushes to this device — try again shortly")

    sender = app.state.fcm_sender
    if sender is None:
        raise HTTPException(status_code=503, detail="FCM is not configured on this relay")

    try:
        provider_id = await sender.send(
            request.token, request.title, request.body, platform=request.platform, data=request.data
        )
    except PushSendError as e:
        logger.warning(f"FCM push failed: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return PushResponse(sent=True, platform=request.platform, provider_id=provider_id or None)
