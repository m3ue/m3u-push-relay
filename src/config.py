from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

VERSION = "0.1.0"


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    """

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8090
    LOG_LEVEL: str = "info"
    RELOAD: bool = False
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"

    # No shared-secret auth: self-hosted apps calling this relay ship any
    # secret in their own publicly-distributed source/images, so it can't be
    # kept private anyway. Rate limits are the actual abuse guard instead.
    RATE_LIMIT_PER_IP_PER_MINUTE: int = 60
    RATE_LIMIT_PER_TOKEN_PER_HOUR: int = 20

    # FCM (Firebase) — handles both Android and iOS delivery. iOS/APNs works
    # because the APNs auth key (.p8) is uploaded directly to the Firebase
    # console for the iOS app; this relay only ever holds the Firebase
    # service account credential, never raw Apple credentials.
    FCM_SERVICE_ACCOUNT_PATH: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="",
        extra="ignore",
    )

    @property
    def fcm_configured(self) -> bool:
        return bool(self.FCM_SERVICE_ACCOUNT_PATH)


settings = Settings()
