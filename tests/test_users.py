"""Tests for SCIM user endpoints."""

import pytest

ENTERPRISE_URN_V1 = "urn:scim:schemas:extension:enterprise:1.0"
ENTERPRISE_URN_V2 = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"


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


class TestFullSchemaAttributes:
    """Tests for full SCIM 1.1 schema compliance — all attributes round-trip."""

    @pytest.mark.asyncio
    async def test_all_attributes_round_trip_v1(self, client, sample_user):
        """Create a user with all attributes and verify they come back."""
        create_resp = await client.post("/scim/v1/Users", json=sample_user)
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        get_resp = await client.get(f"/scim/v1/Users/{user_id}")
        data = get_resp.json()

        # Singular attributes
        assert data["nickName"] == "Johnny"
        assert data["profileUrl"] == "https://example.com/jdoe"
        assert data["title"] == "Software Engineer"
        assert data["userType"] == "Employee"
        assert data["preferredLanguage"] == "en-US"
        assert data["locale"] == "en-US"
        assert data["timezone"] == "America/New_York"

        # Multi-valued attributes
        assert len(data["phoneNumbers"]) == 1
        assert data["phoneNumbers"][0]["value"] == "+1-555-0100"
        assert data["ims"][0]["value"] == "jdoe_im"
        assert data["photos"][0]["value"] == "https://example.com/jdoe/photo.jpg"
        assert data["addresses"][0]["streetAddress"] == "123 Main St"
        assert data["addresses"][0]["locality"] == "Springfield"
        assert data["entitlements"][0]["value"] == "full-access"
        assert data["roles"][0]["value"] == "developer"
        assert data["x509Certificates"][0]["value"] == "MIID...(base64)..."

    @pytest.mark.asyncio
    async def test_all_attributes_round_trip_v2(self, client, sample_user):
        """Same round-trip test via v2 endpoints."""
        create_resp = await client.post("/scim/v2/Users", json=sample_user)
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        get_resp = await client.get(f"/scim/v2/Users/{user_id}")
        data = get_resp.json()

        assert data["nickName"] == "Johnny"
        assert data["title"] == "Software Engineer"
        assert len(data["phoneNumbers"]) == 1
        assert data["addresses"][0]["country"] == "US"
        assert data["roles"][0]["primary"] is True

    @pytest.mark.asyncio
    async def test_minimal_user_omits_optional_attrs(self, client, sample_user_minimal):
        """A minimal user should not have optional attributes in the response."""
        create_resp = await client.post("/scim/v1/Users", json=sample_user_minimal)
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        get_resp = await client.get(f"/scim/v1/Users/{user_id}")
        data = get_resp.json()

        # These should not be present since they weren't provided
        for attr in ["nickName", "phoneNumbers", "ims", "photos",
                     "addresses", "entitlements", "roles", "x509Certificates"]:
            assert attr not in data


class TestPasswordWriteOnly:
    """Test that password is write-only — accepted on input, never in output."""

    @pytest.mark.asyncio
    async def test_password_not_in_create_response_v1(self, client, sample_user):
        resp = await client.post("/scim/v1/Users", json=sample_user)
        assert resp.status_code == 201
        assert "password" not in resp.json()

    @pytest.mark.asyncio
    async def test_password_not_in_get_response_v1(self, client, sample_user):
        create_resp = await client.post("/scim/v1/Users", json=sample_user)
        user_id = create_resp.json()["id"]
        get_resp = await client.get(f"/scim/v1/Users/{user_id}")
        assert "password" not in get_resp.json()

    @pytest.mark.asyncio
    async def test_password_not_in_create_response_v2(self, client, sample_user):
        resp = await client.post("/scim/v2/Users", json=sample_user)
        assert resp.status_code == 201
        assert "password" not in resp.json()

    @pytest.mark.asyncio
    async def test_password_not_in_put_response_v1(self, client, sample_user):
        create_resp = await client.post("/scim/v1/Users", json=sample_user)
        user_id = create_resp.json()["id"]
        resp = await client.put(f"/scim/v1/Users/{user_id}", json=sample_user)
        assert "password" not in resp.json()

    @pytest.mark.asyncio
    async def test_password_not_in_list_response_v1(self, client, sample_user):
        await client.post("/scim/v1/Users", json=sample_user)
        resp = await client.get("/scim/v1/Users")
        for resource in resp.json()["Resources"]:
            assert "password" not in resource


class TestReadOnlyGroups:
    """Test read-only `groups` attribute on User responses."""

    @pytest.mark.asyncio
    async def test_groups_populated_after_group_membership(self, client, sample_user):
        """Create user, create group with user, GET user → groups populated."""
        create_resp = await client.post("/scim/v1/Users", json=sample_user)
        user_id = create_resp.json()["id"]

        # Create a group with this user as member
        group_data = {
            "displayName": "Engineering",
            "members": [{"value": user_id}],
        }
        group_resp = await client.post("/scim/v1/Groups", json=group_data)
        assert group_resp.status_code == 201
        group_id = group_resp.json()["id"]

        # GET user should include groups
        get_resp = await client.get(f"/scim/v1/Users/{user_id}")
        data = get_resp.json()
        assert "groups" in data
        assert len(data["groups"]) == 1
        assert data["groups"][0]["value"] == group_id
        assert data["groups"][0]["display"] == "Engineering"
        assert data["groups"][0]["type"] == "direct"

    @pytest.mark.asyncio
    async def test_groups_populated_v2(self, client, sample_user):
        """Same test via v2."""
        create_resp = await client.post("/scim/v2/Users", json=sample_user)
        user_id = create_resp.json()["id"]

        group_data = {
            "displayName": "Backend",
            "members": [{"value": user_id}],
        }
        await client.post("/scim/v2/Groups", json=group_data)

        get_resp = await client.get(f"/scim/v2/Users/{user_id}")
        data = get_resp.json()
        assert "groups" in data
        assert data["groups"][0]["display"] == "Backend"

    @pytest.mark.asyncio
    async def test_no_groups_when_not_member(self, client, sample_user):
        """User not in any group should not have groups attribute."""
        create_resp = await client.post("/scim/v1/Users", json=sample_user)
        user_id = create_resp.json()["id"]

        get_resp = await client.get(f"/scim/v1/Users/{user_id}")
        data = get_resp.json()
        assert "groups" not in data

    @pytest.mark.asyncio
    async def test_multiple_group_memberships(self, client, sample_user):
        """User in multiple groups should have all listed."""
        create_resp = await client.post("/scim/v1/Users", json=sample_user)
        user_id = create_resp.json()["id"]

        for name in ["Alpha", "Beta", "Gamma"]:
            await client.post("/scim/v1/Groups", json={
                "displayName": name,
                "members": [{"value": user_id}],
            })

        get_resp = await client.get(f"/scim/v1/Users/{user_id}")
        data = get_resp.json()
        assert len(data["groups"]) == 3
        group_names = {g["display"] for g in data["groups"]}
        assert group_names == {"Alpha", "Beta", "Gamma"}


class TestEnterpriseExtension:
    """Test enterprise user extension."""

    @pytest.mark.asyncio
    async def test_enterprise_extension_v1(self, client, sample_user):
        """Create user with enterprise extension via v1, verify round-trip."""
        user_with_ext = {
            **sample_user,
            ENTERPRISE_URN_V1: {
                "employeeNumber": "E12345",
                "costCenter": "CC100",
                "organization": "Acme Corp",
                "division": "Engineering",
                "department": "Platform",
                "manager": {
                    "managerId": "mgr-001",
                    "displayName": "Jane Manager",
                },
            },
        }
        create_resp = await client.post("/scim/v1/Users", json=user_with_ext)
        assert create_resp.status_code == 201
        data = create_resp.json()

        # Enterprise extension should be present under v1 URN
        assert ENTERPRISE_URN_V1 in data
        ext = data[ENTERPRISE_URN_V1]
        assert ext["employeeNumber"] == "E12345"
        assert ext["costCenter"] == "CC100"
        assert ext["organization"] == "Acme Corp"
        assert ext["division"] == "Engineering"
        assert ext["department"] == "Platform"
        assert ext["manager"]["managerId"] == "mgr-001"
        assert ext["manager"]["displayName"] == "Jane Manager"

        # Enterprise URN should be in schemas
        assert ENTERPRISE_URN_V1 in data["schemas"]

    @pytest.mark.asyncio
    async def test_enterprise_extension_v2(self, client, sample_user):
        """Create user with enterprise extension via v2, verify round-trip."""
        user_with_ext = {
            **sample_user,
            ENTERPRISE_URN_V2: {
                "employeeNumber": "E67890",
                "department": "Sales",
            },
        }
        create_resp = await client.post("/scim/v2/Users", json=user_with_ext)
        assert create_resp.status_code == 201
        data = create_resp.json()

        assert ENTERPRISE_URN_V2 in data
        assert data[ENTERPRISE_URN_V2]["employeeNumber"] == "E67890"
        assert data[ENTERPRISE_URN_V2]["department"] == "Sales"
        assert ENTERPRISE_URN_V2 in data["schemas"]

    @pytest.mark.asyncio
    async def test_enterprise_extension_get_v1(self, client, sample_user):
        """GET should return enterprise extension if it was stored."""
        user_with_ext = {
            **sample_user,
            ENTERPRISE_URN_V1: {"employeeNumber": "E111"},
        }
        create_resp = await client.post("/scim/v1/Users", json=user_with_ext)
        user_id = create_resp.json()["id"]

        get_resp = await client.get(f"/scim/v1/Users/{user_id}")
        data = get_resp.json()
        assert ENTERPRISE_URN_V1 in data
        assert data[ENTERPRISE_URN_V1]["employeeNumber"] == "E111"

    @pytest.mark.asyncio
    async def test_no_enterprise_extension_when_not_provided(self, client, sample_user_minimal):
        """User without enterprise extension should not have it in response."""
        create_resp = await client.post("/scim/v1/Users", json=sample_user_minimal)
        user_id = create_resp.json()["id"]

        get_resp = await client.get(f"/scim/v1/Users/{user_id}")
        data = get_resp.json()
        assert ENTERPRISE_URN_V1 not in data
        assert len(data["schemas"]) == 1


class TestPatchWithNewAttributes:
    """Test PATCH operations with new attributes."""

    @pytest.mark.asyncio
    async def test_patch_v1_new_attrs(self, client, sample_user_minimal):
        """PATCH v1 to add new attributes."""
        create_resp = await client.post("/scim/v1/Users", json=sample_user_minimal)
        user_id = create_resp.json()["id"]

        patch_body = {
            "title": "Staff Engineer",
            "nickName": "JD",
            "phoneNumbers": [{"value": "+1-555-0200", "type": "mobile"}],
        }
        patch_resp = await client.patch(f"/scim/v1/Users/{user_id}", json=patch_body)
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["title"] == "Staff Engineer"
        assert data["nickName"] == "JD"
        assert data["phoneNumbers"][0]["value"] == "+1-555-0200"

    @pytest.mark.asyncio
    async def test_patch_v2_operations_new_attrs(self, client, sample_user_minimal):
        """PATCH v2 with Operations to add new attributes."""
        create_resp = await client.post("/scim/v2/Users", json=sample_user_minimal)
        user_id = create_resp.json()["id"]

        patch_body = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "replace", "path": "title", "value": "Principal Engineer"},
                {"op": "add", "path": "nickName", "value": "JD"},
            ],
        }
        patch_resp = await client.patch(f"/scim/v2/Users/{user_id}", json=patch_body)
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["title"] == "Principal Engineer"
        assert data["nickName"] == "JD"

    @pytest.mark.asyncio
    async def test_patch_v1_enterprise_extension(self, client, sample_user_minimal):
        """PATCH v1 to add enterprise extension."""
        create_resp = await client.post("/scim/v1/Users", json=sample_user_minimal)
        user_id = create_resp.json()["id"]

        patch_body = {
            ENTERPRISE_URN_V1: {
                "department": "Finance",
                "employeeNumber": "F999",
            },
        }
        patch_resp = await client.patch(f"/scim/v1/Users/{user_id}", json=patch_body)
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert ENTERPRISE_URN_V1 in data
        assert data[ENTERPRISE_URN_V1]["department"] == "Finance"

    @pytest.mark.asyncio
    async def test_put_updates_all_attrs_v1(self, client, sample_user):
        """PUT v1 updates all attributes including new ones."""
        create_resp = await client.post("/scim/v1/Users", json=sample_user)
        user_id = create_resp.json()["id"]

        updated = {**sample_user, "title": "VP of Engineering", "nickName": "JohnnyV"}
        put_resp = await client.put(f"/scim/v1/Users/{user_id}", json=updated)
        assert put_resp.status_code == 200
        data = put_resp.json()
        assert data["title"] == "VP of Engineering"
        assert data["nickName"] == "JohnnyV"
