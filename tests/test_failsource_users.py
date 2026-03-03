"""Tests for FailSource-style User endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from scim_server.failsource_routes import _active_tokens
from scim_server.failsource_storage import fs_storage
from scim_server.main import app

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
    """Unauthenticated client for token + bearer requests."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def bearer_token(client):
    """Obtain a valid bearer token."""
    resp = await client.post(
        "/services/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "test-id",
            "client_secret": "test-secret",
        },
    )
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(bearer_token):
    return {"Authorization": f"Bearer {bearer_token}"}


class TestUserCrud:

    @pytest.mark.asyncio
    async def test_create_user(self, client, auth_headers):
        response = await client.post(
            "/services/data/v62.0/sobjects/User",
            json={
                "Username": "jdoe@example.com",
                "FirstName": "John",
                "LastName": "Doe",
                "Email": "jdoe@example.com",
                "IsActive": True,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "Id" in data
        assert data["errors"] == []

    @pytest.mark.asyncio
    async def test_get_user(self, client, auth_headers):
        # Create first
        create_resp = await client.post(
            "/services/data/v62.0/sobjects/User",
            json={"Username": "jdoe@example.com", "FirstName": "John", "LastName": "Doe"},
            headers=auth_headers,
        )
        user_id = create_resp.json()["Id"]

        # Read
        response = await client.get(
            f"/services/data/v62.0/sobjects/User/{user_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["Id"] == user_id
        assert data["Username"] == "jdoe@example.com"
        assert data["FirstName"] == "John"
        assert data["LastName"] == "Doe"
        assert data["attributes"]["type"] == "User"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, client, auth_headers):
        response = await client.get(
            "/services/data/v62.0/sobjects/User/nonexistent-id",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user(self, client, auth_headers):
        # Create
        create_resp = await client.post(
            "/services/data/v62.0/sobjects/User",
            json={"Username": "jdoe@example.com", "FirstName": "John", "LastName": "Doe"},
            headers=auth_headers,
        )
        user_id = create_resp.json()["Id"]

        # Update
        response = await client.patch(
            f"/services/data/v62.0/sobjects/User/{user_id}",
            json={"FirstName": "Jane"},
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify
        get_resp = await client.get(
            f"/services/data/v62.0/sobjects/User/{user_id}",
            headers=auth_headers,
        )
        assert get_resp.json()["FirstName"] == "Jane"

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, client, auth_headers):
        response = await client.patch(
            "/services/data/v62.0/sobjects/User/nonexistent-id",
            json={"FirstName": "Ghost"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_user(self, client, auth_headers):
        # Create
        create_resp = await client.post(
            "/services/data/v62.0/sobjects/User",
            json={"Username": "deleteme@example.com", "FirstName": "Del", "LastName": "Ete"},
            headers=auth_headers,
        )
        user_id = create_resp.json()["Id"]

        # Delete
        response = await client.delete(
            f"/services/data/v62.0/sobjects/User/{user_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify gone
        get_resp = await client.get(
            f"/services/data/v62.0/sobjects/User/{user_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, client, auth_headers):
        response = await client.delete(
            "/services/data/v62.0/sobjects/User/nonexistent-id",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_users(self, client, auth_headers):
        # Create two users
        await client.post(
            "/services/data/v62.0/sobjects/User",
            json={"Username": "user1@example.com", "FirstName": "User", "LastName": "One"},
            headers=auth_headers,
        )
        await client.post(
            "/services/data/v62.0/sobjects/User",
            json={"Username": "user2@example.com", "FirstName": "User", "LastName": "Two"},
            headers=auth_headers,
        )

        response = await client.get(
            "/services/data/v62.0/sobjects/User",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalSize"] == 2
        assert data["done"] is True
        assert len(data["records"]) == 2


class TestUserPagination:

    @pytest.mark.asyncio
    async def test_pagination(self, client, auth_headers, monkeypatch):
        monkeypatch.setenv("FS_PAGE_SIZE", "2")

        # Create 5 users
        for i in range(5):
            await client.post(
                "/services/data/v62.0/sobjects/User",
                json={
                    "Username": f"user{i}@example.com",
                    "FirstName": f"User{i}",
                    "LastName": "Test",
                },
                headers=auth_headers,
            )

        # First page
        response = await client.get(
            "/services/data/v62.0/sobjects/User",
            headers=auth_headers,
        )
        data = response.json()
        assert data["totalSize"] == 5
        assert data["done"] is False
        assert len(data["records"]) == 2
        assert "nextRecordsUrl" in data

        # Second page
        next_url = data["nextRecordsUrl"]
        response2 = await client.get(next_url, headers=auth_headers)
        data2 = response2.json()
        assert len(data2["records"]) == 2
        assert data2["done"] is False

        # Third page (last)
        next_url2 = data2["nextRecordsUrl"]
        response3 = await client.get(next_url2, headers=auth_headers)
        data3 = response3.json()
        assert len(data3["records"]) == 1
        assert data3["done"] is True
        assert "nextRecordsUrl" not in data3

    @pytest.mark.asyncio
    async def test_expired_page_returns_404(self, client, auth_headers):
        response = await client.get(
            "/services/data/v62.0/query/nonexistent-page-id",
            headers=auth_headers,
        )
        assert response.status_code == 404
