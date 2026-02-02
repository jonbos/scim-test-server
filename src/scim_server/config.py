"""
Server configuration with presets and granular overrides.

Configuration precedence (highest to lowest):
1. Runtime overrides (via API)
2. Environment variable overrides (e.g., SCIM_GROUPS_PUT=false)
3. Preset defaults (from SCIM_PRESET)
4. Base defaults (permissive)

Environment variables:
- SCIM_PRESET: Base preset (permissive, pingdirectory, put_only)
- SCIM_GROUPS_PUT: Override groups PUT support (true/false)
- SCIM_GROUPS_PATCH: Override groups PATCH support (true/false)
- Future: SCIM_USERS_*, etc.
"""

import os
from dataclasses import dataclass, field
from typing import Any


# Preset definitions - each preset defines defaults for all settings
PRESETS: dict[str, dict[str, bool]] = {
    "permissive": {
        "groups_put": True,
        "groups_patch": True,
    },
    "pingdirectory": {
        "groups_put": False,
        "groups_patch": True,
    },
    "put_only": {
        "groups_put": True,
        "groups_patch": False,
    },
}

DEFAULT_PRESET = "permissive"


def _parse_bool(value: str | None) -> bool | None:
    """Parse a boolean from string, returning None if not set."""
    if value is None:
        return None
    return value.lower() in ("true", "1", "yes", "on")


@dataclass
class ScimConfig:
    """SCIM server configuration with preset support and granular overrides."""

    # The active preset name
    preset: str = DEFAULT_PRESET

    # Granular overrides (None means use preset default)
    _overrides: dict[str, bool] = field(default_factory=dict)

    def __post_init__(self):
        if self.preset not in PRESETS:
            valid = ", ".join(PRESETS.keys())
            raise ValueError(f"Invalid preset '{self.preset}'. Valid presets: {valid}")

    def _get_setting(self, key: str) -> bool:
        """Get effective value for a setting (override > preset)."""
        if key in self._overrides:
            return self._overrides[key]
        return PRESETS[self.preset].get(key, True)

    # Groups settings
    @property
    def groups_put(self) -> bool:
        return self._get_setting("groups_put")

    @property
    def groups_patch(self) -> bool:
        return self._get_setting("groups_patch")

    # Methods for runtime changes
    def set_preset(self, preset: str) -> None:
        """Change the active preset. Clears all overrides."""
        if preset not in PRESETS:
            valid = ", ".join(PRESETS.keys())
            raise ValueError(f"Invalid preset '{preset}'. Valid presets: {valid}")
        self.preset = preset
        self._overrides.clear()

    def set_override(self, key: str, value: bool) -> None:
        """Set a granular override."""
        valid_keys = set()
        for preset_settings in PRESETS.values():
            valid_keys.update(preset_settings.keys())
        if key not in valid_keys:
            raise ValueError(f"Invalid setting '{key}'. Valid settings: {', '.join(sorted(valid_keys))}")
        self._overrides[key] = value

    def clear_override(self, key: str) -> None:
        """Clear a specific override, reverting to preset default."""
        self._overrides.pop(key, None)

    def clear_all_overrides(self) -> None:
        """Clear all overrides, reverting to preset defaults."""
        self._overrides.clear()

    def to_dict(self) -> dict[str, Any]:
        """Return current effective configuration as a dictionary."""
        return {
            "preset": self.preset,
            "effective": {
                "groups_put": self.groups_put,
                "groups_patch": self.groups_patch,
            },
            "overrides": dict(self._overrides),
        }


def _load_config_from_env() -> ScimConfig:
    """Load configuration from environment variables."""
    preset = os.environ.get("SCIM_PRESET", DEFAULT_PRESET).lower()
    config = ScimConfig(preset=preset)

    # Apply environment variable overrides
    groups_put = _parse_bool(os.environ.get("SCIM_GROUPS_PUT"))
    if groups_put is not None:
        config.set_override("groups_put", groups_put)

    groups_patch = _parse_bool(os.environ.get("SCIM_GROUPS_PATCH"))
    if groups_patch is not None:
        config.set_override("groups_patch", groups_patch)

    return config


# Global config instance
config = _load_config_from_env()


# Convenience functions for backwards compatibility
def allows_put_for_groups() -> bool:
    """Returns True if PUT is allowed for group updates."""
    return config.groups_put


def allows_patch_for_groups() -> bool:
    """Returns True if PATCH is allowed for group updates."""
    return config.groups_patch


def get_config() -> ScimConfig:
    """Get the global config instance."""
    return config


def reload_config() -> ScimConfig:
    """Reload configuration from environment variables."""
    global config
    config = _load_config_from_env()
    return config
