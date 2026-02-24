"""Tests for configuration system."""

import pytest

from scim_server.config import ScimConfig


class TestScimConfig:
    """Tests for ScimConfig class."""

    def test_default_preset_is_permissive(self):
        cfg = ScimConfig()
        assert cfg.preset == "permissive"
        assert cfg.groups_put is True
        assert cfg.groups_patch is True

    def test_pingdirectory_preset(self):
        cfg = ScimConfig(preset="pingdirectory")
        assert cfg.groups_put is False
        assert cfg.groups_patch is True

    def test_put_only_preset(self):
        cfg = ScimConfig(preset="put_only")
        assert cfg.groups_put is True
        assert cfg.groups_patch is False

    def test_invalid_preset_raises(self):
        with pytest.raises(ValueError, match="Invalid preset"):
            ScimConfig(preset="invalid")

    def test_override_takes_precedence(self):
        cfg = ScimConfig(preset="permissive")
        assert cfg.groups_put is True

        cfg.set_override("groups_put", False)
        assert cfg.groups_put is False

    def test_clear_override_reverts_to_preset(self):
        cfg = ScimConfig(preset="permissive")
        cfg.set_override("groups_put", False)
        assert cfg.groups_put is False

        cfg.clear_override("groups_put")
        assert cfg.groups_put is True

    def test_set_preset_clears_overrides(self):
        cfg = ScimConfig(preset="permissive")
        cfg.set_override("groups_put", False)
        assert cfg.groups_put is False

        cfg.set_preset("pingdirectory")
        # Override should be cleared, pingdirectory default is False
        assert cfg.groups_put is False
        # But it's from preset, not override
        assert "groups_put" not in cfg._overrides

    def test_invalid_override_key_raises(self):
        cfg = ScimConfig()
        with pytest.raises(ValueError, match="Invalid setting"):
            cfg.set_override("invalid_key", True)

    def test_to_dict(self):
        cfg = ScimConfig(preset="pingdirectory")
        cfg.set_override("groups_patch", False)

        result = cfg.to_dict()
        assert result["preset"] == "pingdirectory"
        assert result["effective"]["groups_put"] is False
        assert result["effective"]["groups_patch"] is False
        assert result["overrides"] == {"groups_patch": False}


class TestConfigAPI:
    """Tests for config API endpoints."""

    @pytest.mark.asyncio
    async def test_get_config(self, client):
        response = await client.get("/admin/config")
        assert response.status_code == 200
        data = response.json()
        assert "preset" in data
        assert "effective" in data
        assert "overrides" in data

    @pytest.mark.asyncio
    async def test_set_preset(self, client):
        response = await client.put("/admin/preset/pingdirectory")
        assert response.status_code == 200
        data = response.json()
        assert data["config"]["preset"] == "pingdirectory"

    @pytest.mark.asyncio
    async def test_set_invalid_preset(self, client):
        response = await client.put("/admin/preset/invalid")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_set_override(self, client):
        response = await client.put("/admin/config/groups_put?value=false")
        assert response.status_code == 200
        data = response.json()
        assert data["config"]["effective"]["groups_put"] is False
        assert data["config"]["overrides"]["groups_put"] is False

    @pytest.mark.asyncio
    async def test_clear_override(self, client):
        # First set an override
        await client.put("/admin/config/groups_put?value=false")

        # Then clear it
        response = await client.delete("/admin/config/groups_put")
        assert response.status_code == 200
        data = response.json()
        assert "groups_put" not in data["config"]["overrides"]

    @pytest.mark.asyncio
    async def test_status_includes_config(self, client):
        response = await client.get("/admin/status")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "users" in data
        assert "groups" in data
