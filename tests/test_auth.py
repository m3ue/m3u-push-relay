from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_secret():
    from api import app

    with patch("auth.settings") as mock_settings:
        mock_settings.RELAY_SHARED_SECRET = "test_secret_123"
        with patch("api._build_apns_sender", return_value=None), patch(
            "api._build_fcm_sender", return_value=None
        ):
            with TestClient(app) as client:
                yield client


@pytest.fixture
def client_without_secret():
    from api import app

    with patch("auth.settings") as mock_settings:
        mock_settings.RELAY_SHARED_SECRET = None
        with patch("api._build_apns_sender", return_value=None), patch(
            "api._build_fcm_sender", return_value=None
        ):
            with TestClient(app) as client:
                yield client


PUSH_BODY = {"token": "tok", "platform": "android", "title": "Hi", "body": "There"}


class TestSharedSecretAuth:
    def test_push_without_secret_header_rejected(self, client_with_secret):
        response = client_with_secret.post("/push", json=PUSH_BODY)
        assert response.status_code == 401

    def test_push_with_wrong_secret_rejected(self, client_with_secret):
        response = client_with_secret.post(
            "/push", json=PUSH_BODY, headers={"X-Relay-Secret": "wrong"}
        )
        assert response.status_code == 403

    def test_push_with_correct_secret_passes_auth(self, client_with_secret):
        response = client_with_secret.post(
            "/push", json=PUSH_BODY, headers={"X-Relay-Secret": "test_secret_123"}
        )
        # FCM sender is stubbed to None here, so auth passes but the request
        # fails downstream with 503 (not configured) — never 401/403.
        assert response.status_code not in (401, 403)
        assert response.status_code == 503

    def test_health_never_requires_secret(self, client_with_secret):
        response = client_with_secret.get("/health")
        assert response.status_code == 200

    def test_push_allowed_when_secret_unset(self, client_without_secret):
        response = client_without_secret.post("/push", json=PUSH_BODY)
        assert response.status_code not in (401, 403)
