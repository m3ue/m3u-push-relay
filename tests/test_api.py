from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_no_providers():
    from api import app

    with patch("auth.settings") as mock_settings:
        mock_settings.RELAY_SHARED_SECRET = None
        with patch("api._build_apns_sender", return_value=None), patch(
            "api._build_fcm_sender", return_value=None
        ):
            with TestClient(app) as client:
                yield client


@pytest.fixture
def client_with_fake_senders():
    from api import app

    fake_apns = AsyncMock()
    fake_apns.send.return_value = "apns-id-1"
    fake_fcm = AsyncMock()
    fake_fcm.send.return_value = "projects/p/messages/1"

    with patch("auth.settings") as mock_settings:
        mock_settings.RELAY_SHARED_SECRET = None
        with patch("api._build_apns_sender", return_value=fake_apns), patch(
            "api._build_fcm_sender", return_value=fake_fcm
        ):
            with TestClient(app) as client:
                yield client, fake_apns, fake_fcm


class TestHealth:
    def test_health_reports_provider_configuration(self, client_no_providers):
        response = client_no_providers.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["apns_configured"] is False
        assert body["fcm_configured"] is False


class TestPushRouting:
    def test_ios_push_routes_to_apns_sender(self, client_with_fake_senders):
        client, fake_apns, fake_fcm = client_with_fake_senders
        response = client.post(
            "/push",
            json={"token": "tok", "platform": "ios", "title": "T", "body": "B"},
        )
        assert response.status_code == 200
        assert response.json() == {"sent": True, "platform": "ios", "provider_id": "apns-id-1"}
        fake_apns.send.assert_awaited_once()
        fake_fcm.send.assert_not_called()

    def test_android_push_routes_to_fcm_sender(self, client_with_fake_senders):
        client, fake_apns, fake_fcm = client_with_fake_senders
        response = client.post(
            "/push",
            json={"token": "tok", "platform": "android", "title": "T", "body": "B"},
        )
        assert response.status_code == 200
        assert response.json()["platform"] == "android"
        fake_fcm.send.assert_awaited_once()
        fake_apns.send.assert_not_called()

    def test_push_returns_503_when_provider_not_configured(self, client_no_providers):
        response = client_no_providers.post(
            "/push",
            json={"token": "tok", "platform": "ios", "title": "T", "body": "B"},
        )
        assert response.status_code == 503

    def test_push_rejects_invalid_platform(self, client_no_providers):
        response = client_no_providers.post(
            "/push",
            json={"token": "tok", "platform": "windows", "title": "T", "body": "B"},
        )
        assert response.status_code == 422

    def test_push_propagates_provider_error_as_502(self, client_with_fake_senders):
        client, fake_apns, _ = client_with_fake_senders
        from models import PushSendError

        fake_apns.send.side_effect = PushSendError("BadDeviceToken", status_code=502)

        response = client.post(
            "/push",
            json={"token": "tok", "platform": "ios", "title": "T", "body": "B"},
        )
        assert response.status_code == 502
        assert "BadDeviceToken" in response.json()["detail"]
