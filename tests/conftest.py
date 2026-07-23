import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """The /push rate limiters are module-level singletons (in-memory, no
    shared store) - reset them around every test so usage in one test can't
    trip limits in another."""
    from api import ip_rate_limiter, token_rate_limiter

    ip_rate_limiter._events.clear()
    token_rate_limiter._events.clear()
    yield
    ip_rate_limiter._events.clear()
    token_rate_limiter._events.clear()


@pytest.fixture
def fcm_service_account_file(tmp_path):
    """A throwaway service-account-shaped JSON file (unsigned, for path/parsing tests)."""
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    data = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": pem,
        "client_email": "relay-test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    path = tmp_path / "fcm-service-account.json"
    path.write_text(json.dumps(data))
    return str(path)
