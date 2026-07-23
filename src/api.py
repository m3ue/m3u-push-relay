import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException

from auth import verify_shared_secret
from config import VERSION, settings
from models import PushRequest, PushResponse, PushSendError
from senders.fcm import FCMSender

logger = logging.getLogger(__name__)


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


@app.post("/push", dependencies=[Depends(verify_shared_secret)], response_model=PushResponse)
async def push(request: PushRequest):
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
