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

    # Shared-secret auth for the /push endpoint. Leave unset to disable auth
    # (only useful for local testing — never leave unset in production).
    RELAY_SHARED_SECRET: Optional[str] = None

    # Rate limits, independent of the shared secret above. Self-hosted apps
    # that call this relay ship the secret in their own publicly-distributed
    # source/images, so it can't be treated as truly private — these bound
    # how much a "known" secret can be abused, regardless of who holds it.
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
