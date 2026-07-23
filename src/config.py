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

    # APNs (iOS/tvOS)
    APNS_KEY_PATH: Optional[str] = None
    APNS_KEY_ID: Optional[str] = None
    APNS_TEAM_ID: Optional[str] = None
    APNS_TOPIC: Optional[str] = None
    APNS_USE_SANDBOX: bool = False

    # FCM (Android)
    FCM_SERVICE_ACCOUNT_PATH: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="",
        extra="ignore",
    )

    @property
    def apns_configured(self) -> bool:
        return bool(self.APNS_KEY_PATH and self.APNS_KEY_ID and self.APNS_TEAM_ID and self.APNS_TOPIC)

    @property
    def fcm_configured(self) -> bool:
        return bool(self.FCM_SERVICE_ACCOUNT_PATH)


settings = Settings()
