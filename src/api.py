import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException

from auth import verify_shared_secret
from config import VERSION, settings
from models import PushRequest, PushResponse, PushSendError
from senders.apns import APNsSender
from senders.fcm import FCMSender

logger = logging.getLogger(__name__)


def _build_apns_sender() -> APNsSender | None:
    if not settings.apns_configured:
        logger.warning("APNs not configured — iOS/tvOS push requests will fail")
        return None
    return APNsSender(
        key_path=settings.APNS_KEY_PATH,
        key_id=settings.APNS_KEY_ID,
        team_id=settings.APNS_TEAM_ID,
        topic=settings.APNS_TOPIC,
        use_sandbox=settings.APNS_USE_SANDBOX,
    )


def _build_fcm_sender() -> FCMSender | None:
    if not settings.fcm_configured:
        logger.warning("FCM not configured — Android push requests will fail")
        return None
    return FCMSender(service_account_path=settings.FCM_SERVICE_ACCOUNT_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.apns_sender = _build_apns_sender()
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


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": VERSION,
        "apns_configured": settings.apns_configured,
        "fcm_configured": settings.fcm_configured,
    }


@app.post("/push", dependencies=[Depends(verify_shared_secret)], response_model=PushResponse)
async def push(request: PushRequest):
    if request.platform == "ios":
        sender = app.state.apns_sender
        provider_name = "APNs"
    else:
        sender = app.state.fcm_sender
        provider_name = "FCM"

    if sender is None:
        raise HTTPException(status_code=503, detail=f"{provider_name} is not configured on this relay")

    try:
        provider_id = await sender.send(request.token, request.title, request.body, request.data)
    except PushSendError as e:
        logger.warning(f"{provider_name} push failed: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return PushResponse(sent=True, platform=request.platform, provider_id=provider_id or None)
