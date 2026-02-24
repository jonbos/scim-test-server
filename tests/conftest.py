"""Shared test fixtures."""


import pytest
from httpx import ASGITransport, AsyncClient, BasicAuth

from scim_server.config import get_config
from scim_server.main import app
from scim_server.storage import storage

TEST_USERNAME = "testadmin"
TEST_PASSWORD = "testpass"


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    """Reset storage and config before each test."""
    monkeypatch.setenv("BASIC_AUTH_USERNAME", TEST_USERNAME)
    monkeypatch.setenv("BASIC_AUTH_PASSWORD", TEST_PASSWORD)
    storage.clear()
    cfg = get_config()
    cfg.set_preset("permissive")
    yield
    storage.clear()
    cfg.set_preset("permissive")


@pytest.fixture
async def client():
    """Async HTTP client for testing (with auth)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        auth=BasicAuth(TEST_USERNAME, TEST_PASSWORD),
    ) as ac:
        yield ac


@pytest.fixture
def sample_user():
    """Sample user data with full SCIM 1.1 attribute set."""
    return {
        "userName": "jdoe",
        "displayName": "John Doe",
        "nickName": "Johnny",
        "profileUrl": "https://example.com/jdoe",
        "title": "Software Engineer",
        "userType": "Employee",
        "preferredLanguage": "en-US",
        "locale": "en-US",
        "timezone": "America/New_York",
        "password": "s3cret!",
        "emails": [{"value": "jdoe@example.com", "type": "work", "primary": True}],
        "phoneNumbers": [{"value": "+1-555-0100", "type": "work", "primary": True}],
        "ims": [{"value": "jdoe_im", "type": "xmpp"}],
        "photos": [{"value": "https://example.com/jdoe/photo.jpg", "type": "photo"}],
        "addresses": [
            {
                "streetAddress": "123 Main St",
                "locality": "Springfield",
                "region": "IL",
                "postalCode": "62701",
                "country": "US",
                "type": "work",
                "primary": True,
            }
        ],
        "entitlements": [{"value": "full-access", "type": "standard"}],
        "roles": [{"value": "developer", "type": "primary", "primary": True}],
        "x509Certificates": [{"value": "MIID...(base64)...", "type": "pem"}],
        "active": True,
    }


@pytest.fixture
def sample_user_minimal():
    """Minimal user data (backwards-compatible with old tests)."""
    return {
        "userName": "jdoe",
        "displayName": "John Doe",
        "emails": [{"value": "jdoe@example.com", "primary": True}],
        "active": True,
    }


@pytest.fixture
def sample_group():
    """Sample group data."""
    return {
        "displayName": "Engineering",
    }
