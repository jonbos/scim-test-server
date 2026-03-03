"""Tests for FailSource OAuth token endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient, BasicAuth

from scim_server.main import app
from scim_server.failsource_routes import _active_tokens
from scim_server.failsource_storage import fs_storage

TEST_USERNAME = "testadmin"
TEST_PASSWORD = "testpass"


@pytest.fixture(autouse=True)
def reset_fs_state(monkeypatch):
    monkeypatch.setenv("BASIC_AUTH_USERNAME", TEST_USERNAME)
    monkeypatch.setenv("BASIC_AUTH_PASSWORD", TEST_PASSWORD)
    monkeypatch.setenv("FS_CLIENT_ID", "test-id")
    monkeypatch.setenv("FS_CLIENT_SECRET", "test-secret")
    fs_storage.clear()
    _active_tokens.clear()
    yield
    fs_storage.clear()
    _active_tokens.clear()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def authed_client():
    """Client with Basic Auth for admin endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        auth=BasicAuth(TEST_USERNAME, TEST_PASSWORD),
    ) as ac:
        yield ac


class TestOAuthToken:

    @pytest.mark.asyncio
    async def test_valid_credentials_returns_token(self, client):
        response = await client.post(
            "/services/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "test-id",
                "client_secret": "test-secret",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert "instance_url" in data

    @pytest.mark.asyncio
    async def test_invalid_client_id(self, client):
        response = await client.post(
            "/services/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "wrong-id",
                "client_secret": "test-secret",
            },
        )
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_client"

    @pytest.mark.asyncio
    async def test_invalid_client_secret(self, client):
        response = await client.post(
            "/services/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "test-id",
                "client_secret": "wrong-secret",
            },
        )
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_client"

    @pytest.mark.asyncio
    async def test_unsupported_grant_type(self, client):
        response = await client.post(
            "/services/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "test-id",
                "client_secret": "test-secret",
            },
        )
        assert response.status_code == 400
        assert response.json()["error"] == "unsupported_grant_type"

    @pytest.mark.asyncio
    async def test_token_is_usable_on_data_endpoint(self, client):
        # Get a token
        token_resp = await client.post(
            "/services/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "test-id",
                "client_secret": "test-secret",
            },
        )
        token = token_resp.json()["access_token"]

        # Use it on a data endpoint
        response = await client.get(
            "/services/data/v62.0/sobjects/User",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestBearerAuth:

    @pytest.mark.asyncio
    async def test_missing_auth_header_returns_401(self, client):
        response = await client.get("/services/data/v62.0/sobjects/User")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, client):
        response = await client.get(
            "/services/data/v62.0/sobjects/User",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


class TestAdminEndpoints:

    @pytest.mark.asyncio
    async def test_failsource_status(self, authed_client):
        response = await authed_client.get("/admin/failsource/status")
        assert response.status_code == 200
        data = response.json()
        assert data["users"] == 0
        assert data["permission_sets"] == 0
        assert data["assignments"] == 0

    @pytest.mark.asyncio
    async def test_failsource_clear(self, authed_client, client):
        # Create some data first
        token_resp = await client.post(
            "/services/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "test-id",
                "client_secret": "test-secret",
            },
        )
        token = token_resp.json()["access_token"]
        await client.post(
            "/services/data/v62.0/sobjects/User",
            json={"Username": "clearme", "FirstName": "Clear", "LastName": "Me"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify data exists
        status = await authed_client.get("/admin/failsource/status")
        assert status.json()["users"] == 1

        # Clear
        clear_resp = await authed_client.delete("/admin/failsource/clear")
        assert clear_resp.status_code == 200

        # Verify cleared
        status = await authed_client.get("/admin/failsource/status")
        assert status.json()["users"] == 0
