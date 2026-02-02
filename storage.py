"""In-memory storage for SCIM resources."""

import uuid
from datetime import datetime, timezone
from typing import Any


class Storage:
    def __init__(self):
        self.users: dict[str, dict[str, Any]] = {}
        self.groups: dict[str, dict[str, Any]] = {}

    def clear(self):
        self.users.clear()
        self.groups.clear()

    def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        user = {
            "id": user_id,
            "userName": user_data.get("userName"),
            "name": user_data.get("name", {}),
            "emails": user_data.get("emails", []),
            "active": user_data.get("active", True),
            "displayName": user_data.get("displayName"),
            "externalId": user_data.get("externalId"),
            "meta": {
                "created": now,
                "lastModified": now,
                "resourceType": "User",
            },
        }
        self.users[user_id] = user
        return user

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        for user in self.users.values():
            if user.get("userName") == username:
                return user
        return None

    def list_users(
        self, start_index: int = 1, count: int = 100, filter_str: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        users = list(self.users.values())

        if filter_str:
            users = self._apply_filter(users, filter_str)

        total = len(users)
        start = start_index - 1
        end = start + count
        return users[start:end], total

    def update_user(self, user_id: str, user_data: dict[str, Any]) -> dict[str, Any] | None:
        if user_id not in self.users:
            return None

        user = self.users[user_id]
        now = datetime.now(timezone.utc).isoformat()

        for key in ["userName", "name", "emails", "active", "displayName", "externalId"]:
            if key in user_data:
                user[key] = user_data[key]

        user["meta"]["lastModified"] = now
        return user

    def delete_user(self, user_id: str) -> bool:
        if user_id in self.users:
            del self.users[user_id]
            self._remove_user_from_groups(user_id)
            return True
        return False

    def create_group(self, group_data: dict[str, Any]) -> dict[str, Any]:
        group_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        group = {
            "id": group_id,
            "displayName": group_data.get("displayName"),
            "externalId": group_data.get("externalId"),
            "members": group_data.get("members", []),
            "meta": {
                "created": now,
                "lastModified": now,
                "resourceType": "Group",
            },
        }
        self.groups[group_id] = group
        return group

    def get_group(self, group_id: str) -> dict[str, Any] | None:
        return self.groups.get(group_id)

    def list_groups(
        self, start_index: int = 1, count: int = 100, filter_str: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        groups = list(self.groups.values())

        if filter_str:
            groups = self._apply_filter(groups, filter_str)

        total = len(groups)
        start = start_index - 1
        end = start + count
        return groups[start:end], total

    def update_group(self, group_id: str, group_data: dict[str, Any]) -> dict[str, Any] | None:
        if group_id not in self.groups:
            return None

        group = self.groups[group_id]
        now = datetime.now(timezone.utc).isoformat()

        for key in ["displayName", "externalId", "members"]:
            if key in group_data:
                group[key] = group_data[key]

        group["meta"]["lastModified"] = now
        return group

    def delete_group(self, group_id: str) -> bool:
        if group_id in self.groups:
            del self.groups[group_id]
            return True
        return False

    def patch_group_members(
        self, group_id: str, operations: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Apply SCIM 1.1 style member patch operations.

        Operations format: [{"value": "user-id", "operation": "add|delete"}]
        """
        if group_id not in self.groups:
            return None

        group = self.groups[group_id]
        now = datetime.now(timezone.utc).isoformat()
        members = list(group.get("members", []))

        for op in operations:
            member_id = op.get("value")
            if not member_id:
                continue
            operation = op.get("operation", "add").lower()

            if operation == "add":
                if not any(m.get("value") == member_id for m in members):
                    user = self.get_user(member_id)
                    member_entry: dict[str, Any] = {"value": member_id, "type": "User"}
                    if user:
                        member_entry["display"] = user.get("displayName") or user.get(
                            "userName"
                        )
                    members.append(member_entry)
            elif operation == "delete":
                members = [m for m in members if m.get("value") != member_id]

        group["members"] = members
        group["meta"]["lastModified"] = now
        return group

    def _remove_user_from_groups(self, user_id: str):
        for group in self.groups.values():
            group["members"] = [m for m in group["members"] if m.get("value") != user_id]

    def _apply_filter(
        self, resources: list[dict[str, Any]], filter_str: str
    ) -> list[dict[str, Any]]:
        """Basic filter support for userName eq "value" and displayName eq "value"."""
        filter_str = filter_str.strip()

        if " eq " in filter_str:
            parts = filter_str.split(" eq ", 1)
            attr = parts[0].strip()
            value = parts[1].strip().strip('"').strip("'")

            return [r for r in resources if r.get(attr) == value]

        return resources


storage = Storage()
