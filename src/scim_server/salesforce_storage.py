"""In-memory storage for Salesforce-style REST API resources."""

import os
import uuid
from datetime import datetime, timezone
from typing import Any

DEFAULT_PAGE_SIZE = 200


def _page_size() -> int:
    try:
        return int(os.environ.get("SF_PAGE_SIZE", DEFAULT_PAGE_SIZE))
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000+0000")


def _new_id() -> str:
    return str(uuid.uuid4())


class SalesforceStorage:
    """In-memory storage for Users, PermissionSets, and PermissionSetAssignments."""

    def __init__(self):
        self.users: dict[str, dict[str, Any]] = {}
        self.permission_sets: dict[str, dict[str, Any]] = {}
        self.assignments: dict[str, dict[str, Any]] = {}
        self._page_cache: dict[str, list[dict[str, Any]]] = {}

    def clear(self):
        self.users.clear()
        self.permission_sets.clear()
        self.assignments.clear()
        self._page_cache.clear()

    # ── Users ─────────────────────────────────────────────────────────────

    def create_user(self, data: dict[str, Any]) -> dict[str, Any]:
        uid = _new_id()
        now = _now_iso()
        user = {
            "Id": uid,
            "Username": data.get("Username"),
            "FirstName": data.get("FirstName", ""),
            "LastName": data.get("LastName", ""),
            "Email": data.get("Email", ""),
            "Alias": data.get("Alias", ""),
            "IsActive": data.get("IsActive", True),
            "ProfileId": data.get("ProfileId", ""),
            "Department": data.get("Department", ""),
            "CreatedDate": now,
            "LastModifiedDate": now,
            "attributes": {"type": "User", "url": f"/services/data/v62.0/sobjects/User/{uid}"},
        }
        self.users[uid] = user
        return user

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self.users.get(user_id)

    def update_user(self, user_id: str, data: dict[str, Any]) -> bool:
        if user_id not in self.users:
            return False
        user = self.users[user_id]
        read_only = {"Id", "CreatedDate", "attributes"}
        for key, value in data.items():
            if key not in read_only:
                user[key] = value
        user["LastModifiedDate"] = _now_iso()
        return True

    def delete_user(self, user_id: str) -> bool:
        if user_id not in self.users:
            return False
        del self.users[user_id]
        # Also remove any assignments for this user
        to_remove = [
            aid for aid, a in self.assignments.items()
            if a["AssigneeId"] == user_id
        ]
        for aid in to_remove:
            del self.assignments[aid]
        return True

    def list_users(self) -> list[dict[str, Any]]:
        return list(self.users.values())

    def find_users(self, field: str, value: str) -> list[dict[str, Any]]:
        return [u for u in self.users.values() if u.get(field) == value]

    # ── PermissionSets ────────────────────────────────────────────────────

    def create_permission_set(self, data: dict[str, Any]) -> dict[str, Any]:
        pid = _new_id()
        now = _now_iso()
        pset = {
            "Id": pid,
            "Name": data.get("Name", ""),
            "Label": data.get("Label", ""),
            "Description": data.get("Description", ""),
            "CreatedDate": now,
            "LastModifiedDate": now,
            "attributes": {
                "type": "PermissionSet",
                "url": f"/services/data/v62.0/sobjects/PermissionSet/{pid}",
            },
        }
        self.permission_sets[pid] = pset
        return pset

    def get_permission_set(self, ps_id: str) -> dict[str, Any] | None:
        return self.permission_sets.get(ps_id)

    def update_permission_set(self, ps_id: str, data: dict[str, Any]) -> bool:
        if ps_id not in self.permission_sets:
            return False
        pset = self.permission_sets[ps_id]
        read_only = {"Id", "CreatedDate", "attributes"}
        for key, value in data.items():
            if key not in read_only:
                pset[key] = value
        pset["LastModifiedDate"] = _now_iso()
        return True

    def delete_permission_set(self, ps_id: str) -> bool:
        if ps_id not in self.permission_sets:
            return False
        del self.permission_sets[ps_id]
        # Also remove assignments for this permission set
        to_remove = [
            aid for aid, a in self.assignments.items()
            if a["PermissionSetId"] == ps_id
        ]
        for aid in to_remove:
            del self.assignments[aid]
        return True

    def list_permission_sets(self) -> list[dict[str, Any]]:
        return list(self.permission_sets.values())

    def find_permission_sets(self, field: str, value: str) -> list[dict[str, Any]]:
        return [p for p in self.permission_sets.values() if p.get(field) == value]

    # ── PermissionSetAssignments ──────────────────────────────────────────

    def create_assignment(self, data: dict[str, Any]) -> dict[str, Any]:
        aid = _new_id()
        now = _now_iso()
        assignment = {
            "Id": aid,
            "AssigneeId": data.get("AssigneeId", ""),
            "PermissionSetId": data.get("PermissionSetId", ""),
            "CreatedDate": now,
            "LastModifiedDate": now,
            "attributes": {
                "type": "PermissionSetAssignment",
                "url": f"/services/data/v62.0/sobjects/PermissionSetAssignment/{aid}",
            },
        }
        self.assignments[aid] = assignment
        return assignment

    def get_assignment(self, assignment_id: str) -> dict[str, Any] | None:
        return self.assignments.get(assignment_id)

    def delete_assignment(self, assignment_id: str) -> bool:
        if assignment_id not in self.assignments:
            return False
        del self.assignments[assignment_id]
        return True

    def list_assignments(self) -> list[dict[str, Any]]:
        return list(self.assignments.values())

    def get_assignments_for_permission_set(self, ps_id: str) -> list[dict[str, Any]]:
        return [a for a in self.assignments.values() if a["PermissionSetId"] == ps_id]

    def get_assignments_for_user(self, user_id: str) -> list[dict[str, Any]]:
        return [a for a in self.assignments.values() if a["AssigneeId"] == user_id]

    # ── Pagination ────────────────────────────────────────────────────────

    def paginate(
        self, records: list[dict[str, Any]], base_url: str,
    ) -> dict[str, Any]:
        """Return a Salesforce-style paginated response.

        If records exceed page size, stores the remainder in _page_cache
        and returns a nextRecordsUrl.
        """
        page_size = _page_size()
        total = len(records)
        page = records[:page_size]
        remaining = records[page_size:]

        result: dict[str, Any] = {
            "totalSize": total,
            "done": len(remaining) == 0,
            "records": page,
        }

        if remaining:
            page_id = _new_id()
            self._page_cache[page_id] = remaining
            result["nextRecordsUrl"] = f"{base_url}/services/data/v62.0/query/{page_id}"

        return result

    def get_next_page(self, page_id: str, base_url: str) -> dict[str, Any] | None:
        """Retrieve the next page of records from the page cache."""
        remaining = self._page_cache.pop(page_id, None)
        if remaining is None:
            return None
        return self.paginate(remaining, base_url)


sf_storage = SalesforceStorage()
