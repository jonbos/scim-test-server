"""Tests for SCIM user endpoints."""

import pytest


class TestUsersV1:
    """Tests for SCIM 1.1 user endpoints."""

    @pytest.mark.asyncio
    async def test_list_users_empty(self, client):
        response = await client.get("/scim/v1/Users")
        assert response.status_code == 200
        data = response.json()
        assert data["totalResults"] == 0
        assert data["Resources"] == []

    @pytest.mark.asyncio
    async def test_create_user(self, client, sample_user):
        response = await client.post("/scim/v1/Users", json=sample_user)
        assert response.status_code == 201
        data = response.json()
        assert data["userName"] == sample_user["userName"]
        assert data["displayName"] == sample_user["displayName"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_duplicate_user(self, client, sample_user):
        await client.post("/scim/v1/Users", json=sample_user)
        response = await client.post("/scim/v1/Users", json=sample_user)
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_get_user(self, client, sample_user):
        create_response = await client.post("/scim/v1/Users", json=sample_user)
        user_id = create_response.json()["id"]

        response = await client.get(f"/scim/v1/Users/{user_id}")
        assert response.status_code == 200
        assert response.json()["userName"] == sample_user["userName"]

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, client):
        response = await client.get("/scim/v1/Users/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user(self, client, sample_user):
        create_response = await client.post("/scim/v1/Users", json=sample_user)
        user_id = create_response.json()["id"]

        updated = {**sample_user, "displayName": "Jane Doe"}
        response = await client.put(f"/scim/v1/Users/{user_id}", json=updated)
        assert response.status_code == 200
        assert response.json()["displayName"] == "Jane Doe"

    @pytest.mark.asyncio
    async def test_delete_user(self, client, sample_user):
        create_response = await client.post("/scim/v1/Users", json=sample_user)
        user_id = create_response.json()["id"]

        response = await client.delete(f"/scim/v1/Users/{user_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = await client.get(f"/scim/v1/Users/{user_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_users_pagination(self, client):
        # Create 5 users
        for i in range(5):
            await client.post("/scim/v1/Users", json={"userName": f"user{i}"})

        # Get first 2
        response = await client.get("/scim/v1/Users?startIndex=1&count=2")
        data = response.json()
        assert data["totalResults"] == 5
        assert data["itemsPerPage"] == 2
        assert len(data["Resources"]) == 2

    @pytest.mark.asyncio
    async def test_filter_users_by_username(self, client):
        await client.post("/scim/v1/Users", json={"userName": "alice"})
        await client.post("/scim/v1/Users", json={"userName": "bob"})

        response = await client.get('/scim/v1/Users?filter=userName eq "alice"')
        data = response.json()
        assert data["totalResults"] == 1
        assert data["Resources"][0]["userName"] == "alice"


class TestUsersV2:
    """Tests for SCIM 2.0 user endpoints."""

    @pytest.mark.asyncio
    async def test_list_users_empty(self, client):
        response = await client.get("/scim/v2/Users")
        assert response.status_code == 200
        data = response.json()
        assert data["totalResults"] == 0
        assert "urn:ietf:params:scim:api:messages:2.0:ListResponse" in data["schemas"]

    @pytest.mark.asyncio
    async def test_create_user(self, client, sample_user):
        response = await client.post("/scim/v2/Users", json=sample_user)
        assert response.status_code == 201
        data = response.json()
        assert "urn:ietf:params:scim:schemas:core:2.0:User" in data["schemas"]
        assert data["userName"] == sample_user["userName"]

    @pytest.mark.asyncio
    async def test_get_user(self, client, sample_user):
        create_response = await client.post("/scim/v2/Users", json=sample_user)
        user_id = create_response.json()["id"]

        response = await client.get(f"/scim/v2/Users/{user_id}")
        assert response.status_code == 200
        assert "urn:ietf:params:scim:schemas:core:2.0:User" in response.json()["schemas"]

    @pytest.mark.asyncio
    async def test_delete_user(self, client, sample_user):
        create_response = await client.post("/scim/v2/Users", json=sample_user)
        user_id = create_response.json()["id"]

        response = await client.delete(f"/scim/v2/Users/{user_id}")
        assert response.status_code == 204
