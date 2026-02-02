"""Tests for SCIM group endpoints and mode behavior."""

import pytest

from scim_server.config import get_config


class TestGroupsV1:
    """Tests for SCIM 1.1 group endpoints."""

    @pytest.mark.asyncio
    async def test_list_groups_empty(self, client):
        response = await client.get("/scim/v1/Groups")
        assert response.status_code == 200
        data = response.json()
        assert data["totalResults"] == 0

    @pytest.mark.asyncio
    async def test_create_group(self, client, sample_group):
        response = await client.post("/scim/v1/Groups", json=sample_group)
        assert response.status_code == 201
        data = response.json()
        assert data["displayName"] == sample_group["displayName"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_group(self, client, sample_group):
        create_response = await client.post("/scim/v1/Groups", json=sample_group)
        group_id = create_response.json()["id"]

        response = await client.get(f"/scim/v1/Groups/{group_id}")
        assert response.status_code == 200
        assert response.json()["displayName"] == sample_group["displayName"]

    @pytest.mark.asyncio
    async def test_delete_group(self, client, sample_group):
        create_response = await client.post("/scim/v1/Groups", json=sample_group)
        group_id = create_response.json()["id"]

        response = await client.delete(f"/scim/v1/Groups/{group_id}")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_put_group_permissive_mode(self, client, sample_group):
        """PUT should work in permissive mode."""
        create_response = await client.post("/scim/v1/Groups", json=sample_group)
        group_id = create_response.json()["id"]

        updated = {**sample_group, "displayName": "Updated"}
        response = await client.put(f"/scim/v1/Groups/{group_id}", json=updated)
        assert response.status_code == 200
        assert response.json()["displayName"] == "Updated"

    @pytest.mark.asyncio
    async def test_put_group_pingdirectory_mode_rejected(self, client, sample_group):
        """PUT should be rejected in pingdirectory mode."""
        get_config().set_preset("pingdirectory")

        create_response = await client.post("/scim/v1/Groups", json=sample_group)
        group_id = create_response.json()["id"]

        updated = {**sample_group, "displayName": "Updated"}
        response = await client.put(f"/scim/v1/Groups/{group_id}", json=updated)
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_patch_group_permissive_mode(self, client, sample_group, sample_user):
        """PATCH should work in permissive mode."""
        # Create user and group
        user_response = await client.post("/scim/v1/Users", json=sample_user)
        user_id = user_response.json()["id"]

        group_response = await client.post("/scim/v1/Groups", json=sample_group)
        group_id = group_response.json()["id"]

        # PATCH to add member
        patch_data = {
            "schemas": ["urn:scim:schemas:core:1.0"],
            "members": [{"value": user_id, "operation": "add"}],
        }
        response = await client.patch(f"/scim/v1/Groups/{group_id}", json=patch_data)
        assert response.status_code == 200
        assert len(response.json()["members"]) == 1

    @pytest.mark.asyncio
    async def test_patch_group_put_only_mode_rejected(self, client, sample_group, sample_user):
        """PATCH should be rejected in put_only mode."""
        get_config().set_preset("put_only")

        user_response = await client.post("/scim/v1/Users", json=sample_user)
        user_id = user_response.json()["id"]

        group_response = await client.post("/scim/v1/Groups", json=sample_group)
        group_id = group_response.json()["id"]

        patch_data = {
            "schemas": ["urn:scim:schemas:core:1.0"],
            "members": [{"value": user_id, "operation": "add"}],
        }
        response = await client.patch(f"/scim/v1/Groups/{group_id}", json=patch_data)
        assert response.status_code == 405


class TestGroupsV2:
    """Tests for SCIM 2.0 group endpoints."""

    @pytest.mark.asyncio
    async def test_list_groups_empty(self, client):
        response = await client.get("/scim/v2/Groups")
        assert response.status_code == 200
        data = response.json()
        assert "urn:ietf:params:scim:api:messages:2.0:ListResponse" in data["schemas"]

    @pytest.mark.asyncio
    async def test_create_group(self, client, sample_group):
        response = await client.post("/scim/v2/Groups", json=sample_group)
        assert response.status_code == 201
        data = response.json()
        assert "urn:ietf:params:scim:schemas:core:2.0:Group" in data["schemas"]

    @pytest.mark.asyncio
    async def test_patch_group_add_member(self, client, sample_group, sample_user):
        """SCIM 2.0 PATCH to add member."""
        user_response = await client.post("/scim/v2/Users", json=sample_user)
        user_id = user_response.json()["id"]

        group_response = await client.post("/scim/v2/Groups", json=sample_group)
        group_id = group_response.json()["id"]

        patch_data = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "add",
                    "path": "members",
                    "value": [{"value": user_id}],
                }
            ],
        }
        response = await client.patch(f"/scim/v2/Groups/{group_id}", json=patch_data)
        assert response.status_code == 200
        assert len(response.json()["members"]) == 1

    @pytest.mark.asyncio
    async def test_patch_group_remove_member(self, client, sample_group, sample_user):
        """SCIM 2.0 PATCH to remove member."""
        user_response = await client.post("/scim/v2/Users", json=sample_user)
        user_id = user_response.json()["id"]

        group_response = await client.post("/scim/v2/Groups", json=sample_group)
        group_id = group_response.json()["id"]

        # Add member first
        add_patch = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "add", "path": "members", "value": [{"value": user_id}]}],
        }
        await client.patch(f"/scim/v2/Groups/{group_id}", json=add_patch)

        # Remove member
        remove_patch = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "remove", "path": "members", "value": [{"value": user_id}]}],
        }
        response = await client.patch(f"/scim/v2/Groups/{group_id}", json=remove_patch)
        assert response.status_code == 200
        assert len(response.json()["members"]) == 0


class TestConfigOverrides:
    """Tests for granular config overrides."""

    @pytest.mark.asyncio
    async def test_override_allows_put_in_pingdirectory(self, client, sample_group):
        """Override can enable PUT even in pingdirectory preset."""
        cfg = get_config()
        cfg.set_preset("pingdirectory")
        cfg.set_override("groups_put", True)

        create_response = await client.post("/scim/v1/Groups", json=sample_group)
        group_id = create_response.json()["id"]

        updated = {**sample_group, "displayName": "Updated"}
        response = await client.put(f"/scim/v1/Groups/{group_id}", json=updated)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_override_disables_patch_in_permissive(self, client, sample_group, sample_user):
        """Override can disable PATCH even in permissive preset."""
        cfg = get_config()
        cfg.set_override("groups_patch", False)

        user_response = await client.post("/scim/v1/Users", json=sample_user)
        user_id = user_response.json()["id"]

        group_response = await client.post("/scim/v1/Groups", json=sample_group)
        group_id = group_response.json()["id"]

        patch_data = {
            "schemas": ["urn:scim:schemas:core:1.0"],
            "members": [{"value": user_id, "operation": "add"}],
        }
        response = await client.patch(f"/scim/v1/Groups/{group_id}", json=patch_data)
        assert response.status_code == 405
