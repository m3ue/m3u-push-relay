import pytest

from models import PushSendError
from senders.apns import APNsSender

pytestmark = pytest.mark.asyncio


@pytest.fixture
def sender(apns_key_file):
    return APNsSender(
        key_path=apns_key_file,
        key_id="TESTKEYID",
        team_id="TESTTEAMID",
        topic="com.example.app",
        use_sandbox=True,
    )


class TestAPNsSender:
    async def test_send_success_returns_apns_id(self, sender, httpx_mock):
        httpx_mock.add_response(
            method="POST",
            url="https://api.sandbox.push.apple.com/3/device/abc123",
            status_code=200,
            headers={"apns-id": "some-apns-id"},
            json={},
        )

        apns_id = await sender.send("abc123", "Recording done", "Your show finished recording")
        assert apns_id == "some-apns-id"

    async def test_send_failure_raises_push_send_error(self, sender, httpx_mock):
        httpx_mock.add_response(
            method="POST",
            url="https://api.sandbox.push.apple.com/3/device/abc123",
            status_code=400,
            json={"reason": "BadDeviceToken"},
        )

        with pytest.raises(PushSendError, match="BadDeviceToken"):
            await sender.send("abc123", "Title", "Body")

    async def test_uses_production_host_by_default(self, apns_key_file, httpx_mock):
        prod_sender = APNsSender(
            key_path=apns_key_file,
            key_id="TESTKEYID",
            team_id="TESTTEAMID",
            topic="com.example.app",
        )
        httpx_mock.add_response(
            method="POST",
            url="https://api.push.apple.com/3/device/tok",
            status_code=200,
            headers={"apns-id": "id"},
        )
        await prod_sender.send("tok", "Title", "Body")

    async def test_reuses_cached_token_across_sends(self, sender, httpx_mock):
        httpx_mock.add_response(method="POST", status_code=200, headers={"apns-id": "1"})
        httpx_mock.add_response(method="POST", status_code=200, headers={"apns-id": "2"})

        await sender.send("tok1", "Title", "Body")
        token_after_first = sender._cached_token
        await sender.send("tok2", "Title", "Body")

        assert sender._cached_token == token_after_first
