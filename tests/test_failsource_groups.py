"""Tests for FailSource-style PermissionSet and PermissionSetAssignment endpoints."""

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
async def bearer_token(client):
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


class TestPermissionSetCrud:

    @pytest.mark.asyncio
    async def test_create_permission_set(self, client, auth_headers):
        response = await client.post(
            "/services/data/v62.0/sobjects/PermissionSet",
            json={"Name": "AdminAccess", "Label": "Admin Access", "Description": "Full admin"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "Id" in data

    @pytest.mark.asyncio
    async def test_get_permission_set(self, client, auth_headers):
        create_resp = await client.post(
            "/services/data/v62.0/sobjects/PermissionSet",
            json={"Name": "ViewOnly", "Label": "View Only"},
            headers=auth_headers,
        )
        ps_id = create_resp.json()["Id"]

        response = await client.get(
            f"/services/data/v62.0/sobjects/PermissionSet/{ps_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["Id"] == ps_id
        assert data["Name"] == "ViewOnly"
        assert data["Label"] == "View Only"
        assert data["attributes"]["type"] == "PermissionSet"

    @pytest.mark.asyncio
    async def test_get_permission_set_not_found(self, client, auth_headers):
        response = await client.get(
            "/services/data/v62.0/sobjects/PermissionSet/nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_permission_set(self, client, auth_headers):
        create_resp = await client.post(
            "/services/data/v62.0/sobjects/PermissionSet",
            json={"Name": "EditAccess", "Label": "Edit Access"},
            headers=auth_headers,
        )
        ps_id = create_resp.json()["Id"]

        response = await client.patch(
            f"/services/data/v62.0/sobjects/PermissionSet/{ps_id}",
            json={"Label": "Full Edit Access"},
            headers=auth_headers,
        )
        assert response.status_code == 204

        get_resp = await client.get(
            f"/services/data/v62.0/sobjects/PermissionSet/{ps_id}",
            headers=auth_headers,
        )
        assert get_resp.json()["Label"] == "Full Edit Access"

    @pytest.mark.asyncio
    async def test_delete_permission_set(self, client, auth_headers):
        create_resp = await client.post(
            "/services/data/v62.0/sobjects/PermissionSet",
            json={"Name": "ToDelete", "Label": "To Delete"},
            headers=auth_headers,
        )
        ps_id = create_resp.json()["Id"]

        response = await client.delete(
            f"/services/data/v62.0/sobjects/PermissionSet/{ps_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        get_resp = await client.get(
            f"/services/data/v62.0/sobjects/PermissionSet/{ps_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_permission_sets(self, client, auth_headers):
        await client.post(
            "/services/data/v62.0/sobjects/PermissionSet",
            json={"Name": "Set1", "Label": "Set One"},
            headers=auth_headers,
        )
        await client.post(
            "/services/data/v62.0/sobjects/PermissionSet",
            json={"Name": "Set2", "Label": "Set Two"},
            headers=auth_headers,
        )

        response = await client.get(
            "/services/data/v62.0/sobjects/PermissionSet",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalSize"] == 2
        assert data["done"] is True
        assert len(data["records"]) == 2


class TestPermissionSetAssignment:

    @pytest.mark.asyncio
    async def test_create_assignment(self, client, auth_headers):
        # Create user and permission set
        user_resp = await client.post(
            "/services/data/v62.0/sobjects/User",
            json={"Username": "member@example.com", "FirstName": "M", "LastName": "E"},
            headers=auth_headers,
        )
        user_id = user_resp.json()["Id"]

        ps_resp = await client.post(
            "/services/data/v62.0/sobjects/PermissionSet",
            json={"Name": "Access", "Label": "Access"},
            headers=auth_headers,
        )
        ps_id = ps_resp.json()["Id"]

        # Create assignment
        response = await client.post(
            "/services/data/v62.0/sobjects/PermissionSetAssignment",
            json={"AssigneeId": user_id, "PermissionSetId": ps_id},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "Id" in data

    @pytest.mark.asyncio
    async def test_delete_assignment(self, client, auth_headers):
        # Create user and permission set
        user_resp = await client.post(
            "/services/data/v62.0/sobjects/User",
            json={"Username": "member2@example.com", "FirstName": "M", "LastName": "E"},
            headers=auth_headers,
        )
        user_id = user_resp.json()["Id"]

        ps_resp = await client.post(
            "/services/data/v62.0/sobjects/PermissionSet",
            json={"Name": "Access2", "Label": "Access 2"},
            headers=auth_headers,
        )
        ps_id = ps_resp.json()["Id"]

        # Create assignment
        assign_resp = await client.post(
            "/services/data/v62.0/sobjects/PermissionSetAssignment",
            json={"AssigneeId": user_id, "PermissionSetId": ps_id},
            headers=auth_headers,
        )
        assign_id = assign_resp.json()["Id"]

        # Delete assignment
        response = await client.delete(
            f"/services/data/v62.0/sobjects/PermissionSetAssignment/{assign_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_assignment_not_found(self, client, auth_headers):
        response = await client.delete(
            "/services/data/v62.0/sobjects/PermissionSetAssignment/nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_user_cascades_to_assignments(self, client, auth_headers):
        # Create user and permission set
        user_resp = await client.post(
            "/services/data/v62.0/sobjects/User",
            json={"Username": "cascade@example.com", "FirstName": "C", "LastName": "D"},
            headers=auth_headers,
        )
        user_id = user_resp.json()["Id"]

        ps_resp = await client.post(
            "/services/data/v62.0/sobjects/PermissionSet",
            json={"Name": "CascadeSet", "Label": "Cascade Set"},
            headers=auth_headers,
        )
        ps_id = ps_resp.json()["Id"]

        # Create assignment
        await client.post(
            "/services/data/v62.0/sobjects/PermissionSetAssignment",
            json={"AssigneeId": user_id, "PermissionSetId": ps_id},
            headers=auth_headers,
        )

        # Verify assignment exists
        authed_client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            auth=BasicAuth(TEST_USERNAME, TEST_PASSWORD),
        )
        async with authed_client:
            status = await authed_client.get("/admin/failsource/status")
            assert status.json()["assignments"] == 1

        # Delete user
        await client.delete(
            f"/services/data/v62.0/sobjects/User/{user_id}",
            headers=auth_headers,
        )

        # Verify assignment was cascaded
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            auth=BasicAuth(TEST_USERNAME, TEST_PASSWORD),
        ) as authed:
            status = await authed.get("/admin/failsource/status")
            assert status.json()["assignments"] == 0
