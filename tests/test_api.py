from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_no_provider():
    from api import app

    with patch("auth.settings") as mock_settings, patch("api.settings") as mock_api_settings:
        mock_settings.RELAY_SHARED_SECRET = None
        mock_api_settings.fcm_configured = False
        with patch("api._build_fcm_sender", return_value=None):
            with TestClient(app) as client:
                yield client


@pytest.fixture
def client_with_fake_sender():
    from api import app

    fake_fcm = AsyncMock()
    fake_fcm.send.return_value = "projects/p/messages/1"

    with patch("auth.settings") as mock_settings:
        mock_settings.RELAY_SHARED_SECRET = None
        with patch("api._build_fcm_sender", return_value=fake_fcm):
            with TestClient(app) as client:
                yield client, fake_fcm


class TestHealth:
    def test_root_is_healthy_for_platform_health_checks(self, client_no_provider):
        response = client_no_provider.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health_reports_provider_configuration(self, client_no_provider):
        response = client_no_provider.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["fcm_configured"] is False


class TestPushRouting:
    def test_ios_push_routes_through_fcm(self, client_with_fake_sender):
        client, fake_fcm = client_with_fake_sender
        response = client.post(
            "/push",
            json={"token": "tok", "platform": "ios", "title": "T", "body": "B"},
        )
        assert response.status_code == 200
        assert response.json() == {"sent": True, "platform": "ios", "provider_id": "projects/p/messages/1"}
        fake_fcm.send.assert_awaited_once_with("tok", "T", "B", platform="ios", data=None)

    def test_android_push_routes_through_fcm(self, client_with_fake_sender):
        client, fake_fcm = client_with_fake_sender
        response = client.post(
            "/push",
            json={"token": "tok", "platform": "android", "title": "T", "body": "B"},
        )
        assert response.status_code == 200
        assert response.json()["platform"] == "android"
        fake_fcm.send.assert_awaited_once_with("tok", "T", "B", platform="android", data=None)

    def test_push_returns_503_when_provider_not_configured(self, client_no_provider):
        response = client_no_provider.post(
            "/push",
            json={"token": "tok", "platform": "ios", "title": "T", "body": "B"},
        )
        assert response.status_code == 503

    def test_push_rejects_invalid_platform(self, client_no_provider):
        response = client_no_provider.post(
            "/push",
            json={"token": "tok", "platform": "windows", "title": "T", "body": "B"},
        )
        assert response.status_code == 422

    def test_push_propagates_provider_error_as_502(self, client_with_fake_sender):
        client, fake_fcm = client_with_fake_sender
        from models import PushSendError

        fake_fcm.send.side_effect = PushSendError("BadDeviceToken", status_code=502)

        response = client.post(
            "/push",
            json={"token": "tok", "platform": "ios", "title": "T", "body": "B"},
        )
        assert response.status_code == 502
        assert "BadDeviceToken" in response.json()["detail"]
