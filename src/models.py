from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class PushRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Device FCM registration token")
    platform: Literal["ios", "android"]
    title: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    data: Optional[Dict[str, str]] = None


class PushResponse(BaseModel):
    sent: bool
    platform: Literal["ios", "android"]
    provider_id: Optional[str] = None


class PushSendError(Exception):
    """Raised when FCM rejects or fails to deliver a push."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
