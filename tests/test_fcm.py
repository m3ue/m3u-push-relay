from unittest.mock import patch

import pytest

from models import PushSendError
from senders.fcm import FCMSender


@pytest.fixture
def sender(fcm_service_account_file):
    return FCMSender(service_account_path=fcm_service_account_file)


class TestFCMSender:
    def test_project_id_read_from_service_account_file(self, sender):
        assert sender.project_id == "test-project"

    @pytest.mark.asyncio
    async def test_send_success_returns_message_name(self, sender, httpx_mock):
        with patch.object(sender, "_access_token", return_value="fake-token"):
            httpx_mock.add_response(
                method="POST",
                url="https://fcm.googleapis.com/v1/projects/test-project/messages:send",
                status_code=200,
                json={"name": "projects/test-project/messages/123"},
            )

            name = await sender.send("device-token", "Title", "Body", {"key": "value"})
            assert name == "projects/test-project/messages/123"

    @pytest.mark.asyncio
    async def test_send_failure_raises_push_send_error(self, sender, httpx_mock):
        with patch.object(sender, "_access_token", return_value="fake-token"):
            httpx_mock.add_response(
                method="POST",
                url="https://fcm.googleapis.com/v1/projects/test-project/messages:send",
                status_code=404,
                json={"error": {"message": "Requested entity was not found."}},
            )

            with pytest.raises(PushSendError, match="not found"):
                await sender.send("bad-token", "Title", "Body")
