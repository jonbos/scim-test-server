"""Shared test fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient

from scim_server.main import app
from scim_server.storage import storage
from scim_server.config import get_config


@pytest.fixture(autouse=True)
def reset_state():
    """Reset storage and config before each test."""
    storage.clear()
    cfg = get_config()
    cfg.set_preset("permissive")
    yield
    storage.clear()
    cfg.set_preset("permissive")


@pytest.fixture
async def client():
    """Async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def sample_user():
    """Sample user data."""
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
