"""SCIM 1.1 and 2.0 server with in-memory storage."""

from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from scim_server.config import allows_patch_for_groups, allows_put_for_groups, get_config
from scim_server.models import GroupPatchV1, GroupPatchV2, GroupRequest, SeedData, UserRequest
from scim_server.storage import storage

app = FastAPI(title="SCIM Server", description="SCIM 1.1 and 2.0 compliant server")

SCIM_V1_SCHEMA_USER = "urn:scim:schemas:core:1.0"
SCIM_V1_SCHEMA_GROUP = "urn:scim:schemas:core:1.0"
SCIM_V2_SCHEMA_USER = "urn:ietf:params:scim:schemas:core:2.0:User"
SCIM_V2_SCHEMA_GROUP = "urn:ietf:params:scim:schemas:core:2.0:Group"
SCIM_V2_LIST_RESPONSE = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
SCIM_V2_ERROR = "urn:ietf:params:scim:api:messages:2.0:Error"


def format_user_v1(user: dict[str, Any], request: Request) -> dict[str, Any]:
    base_url = str(request.base_url).rstrip("/")
    return {
        "schemas": [SCIM_V1_SCHEMA_USER],
        "id": user["id"],
        "userName": user["userName"],
        "name": user.get("name", {}),
        "displayName": user.get("displayName"),
        "emails": user.get("emails", []),
        "active": user.get("active", True),
        "externalId": user.get("externalId"),
        "meta": {
            **user["meta"],
            "location": f"{base_url}/scim/v1/Users/{user['id']}",
        },
    }


def format_user_v2(user: dict[str, Any], request: Request) -> dict[str, Any]:
    base_url = str(request.base_url).rstrip("/")
    return {
        "schemas": [SCIM_V2_SCHEMA_USER],
        "id": user["id"],
        "userName": user["userName"],
        "name": user.get("name", {}),
        "displayName": user.get("displayName"),
        "emails": user.get("emails", []),
        "active": user.get("active", True),
        "externalId": user.get("externalId"),
        "meta": {
            **user["meta"],
            "location": f"{base_url}/scim/v2/Users/{user['id']}",
        },
    }


def format_group_v1(group: dict[str, Any], request: Request) -> dict[str, Any]:
    base_url = str(request.base_url).rstrip("/")
    return {
        "schemas": [SCIM_V1_SCHEMA_GROUP],
        "id": group["id"],
        "displayName": group["displayName"],
        "externalId": group.get("externalId"),
        "members": group.get("members", []),
        "meta": {
            **group["meta"],
            "location": f"{base_url}/scim/v1/Groups/{group['id']}",
        },
    }


def format_group_v2(group: dict[str, Any], request: Request) -> dict[str, Any]:
    base_url = str(request.base_url).rstrip("/")
    return {
        "schemas": [SCIM_V2_SCHEMA_GROUP],
        "id": group["id"],
        "displayName": group["displayName"],
        "externalId": group.get("externalId"),
        "members": group.get("members", []),
        "meta": {
            **group["meta"],
            "location": f"{base_url}/scim/v2/Groups/{group['id']}",
        },
    }


def scim_error_v1(status: int, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"Errors": [{"description": detail, "code": status}]},
    )


def scim_error_v2(status: int, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "schemas": [SCIM_V2_ERROR],
            "detail": detail,
            "status": status,
        },
    )


# ============================================================================
# Admin endpoints
# ============================================================================


@app.post("/admin/seed")
async def seed_data(data: SeedData):
    """Seed the server with initial users and groups."""
    storage.clear()
    created_users = {}

    if data.users:
        for user in data.users:
            created = storage.create_user(user.model_dump(exclude_none=True))
            created_users[user.userName] = created["id"]

    if data.groups:
        for group in data.groups:
            group_data = {
                "displayName": group.displayName,
                "externalId": group.externalId,
                "members": [],
            }
            if group.members:
                for username in group.members:
                    if username in created_users:
                        user = storage.get_user(created_users[username])
                        if user:
                            group_data["members"].append(
                                {
                                    "value": user["id"],
                                    "display": user.get("displayName") or user["userName"],
                                    "type": "User",
                                }
                            )
            storage.create_group(group_data)

    return {
        "message": "Data seeded successfully",
        "users": len(storage.users),
        "groups": len(storage.groups),
    }


@app.delete("/admin/clear")
async def clear_data():
    """Clear all users and groups."""
    storage.clear()
    return {"message": "All data cleared"}


@app.get("/admin/status")
async def status():
    """Get current server status including configuration."""
    cfg = get_config()
    return {
        "users": len(storage.users),
        "groups": len(storage.groups),
        "config": cfg.to_dict(),
    }


@app.get("/admin/config")
async def get_configuration():
    """Get current configuration details."""
    return get_config().to_dict()


@app.put("/admin/preset/{preset}")
async def set_preset(preset: str):
    """Change the active preset. Clears all overrides."""
    cfg = get_config()
    try:
        cfg.set_preset(preset)
        return {"message": f"Preset changed to '{preset}'", "config": cfg.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/admin/config/{setting}")
async def set_config_override(setting: str, value: bool = Query(..., description="true or false")):
    """Set a configuration override. Overrides take precedence over preset defaults."""
    cfg = get_config()
    try:
        cfg.set_override(setting, value)
        return {"message": f"Override set: {setting}={value}", "config": cfg.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/admin/config/{setting}")
async def clear_config_override(setting: str):
    """Clear a configuration override, reverting to preset default."""
    cfg = get_config()
    cfg.clear_override(setting)
    return {"message": f"Override cleared: {setting}", "config": cfg.to_dict()}


# Legacy endpoint for backwards compatibility
@app.put("/admin/mode/{mode}")
async def change_mode(mode: str):
    """[DEPRECATED] Use /admin/preset/{preset} instead. Changes preset."""
    cfg = get_config()
    try:
        cfg.set_preset(mode)
        return {"message": f"Preset changed to '{mode}'", "config": cfg.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# SCIM v1 Users
# ============================================================================


@app.get("/scim/v1/Users")
async def list_users_v1(
    request: Request,
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=0),
    filter: str | None = None,
):
    users, total = storage.list_users(startIndex, count, filter)
    return {
        "schemas": [SCIM_V1_SCHEMA_USER],
        "totalResults": total,
        "startIndex": startIndex,
        "itemsPerPage": len(users),
        "Resources": [format_user_v1(u, request) for u in users],
    }


@app.get("/scim/v1/Users/{user_id}")
async def get_user_v1(user_id: str, request: Request):
    user = storage.get_user(user_id)
    if not user:
        return scim_error_v1(404, f"User {user_id} not found")
    return format_user_v1(user, request)


@app.post("/scim/v1/Users", status_code=201)
async def create_user_v1(user_data: UserRequest, request: Request):
    if storage.get_user_by_username(user_data.userName):
        return scim_error_v1(409, f"User {user_data.userName} already exists")
    user = storage.create_user(user_data.model_dump(exclude_none=True))
    return format_user_v1(user, request)


@app.put("/scim/v1/Users/{user_id}")
async def update_user_v1(user_id: str, user_data: UserRequest, request: Request):
    user = storage.update_user(user_id, user_data.model_dump(exclude_none=True))
    if not user:
        return scim_error_v1(404, f"User {user_id} not found")
    return format_user_v1(user, request)


@app.delete("/scim/v1/Users/{user_id}", status_code=204)
async def delete_user_v1(user_id: str):
    if not storage.delete_user(user_id):
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return None


# ============================================================================
# SCIM v1 Groups
# ============================================================================


@app.get("/scim/v1/Groups")
async def list_groups_v1(
    request: Request,
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=0),
    filter: str | None = None,
):
    groups, total = storage.list_groups(startIndex, count, filter)
    return {
        "schemas": [SCIM_V1_SCHEMA_GROUP],
        "totalResults": total,
        "startIndex": startIndex,
        "itemsPerPage": len(groups),
        "Resources": [format_group_v1(g, request) for g in groups],
    }


@app.get("/scim/v1/Groups/{group_id}")
async def get_group_v1(group_id: str, request: Request):
    group = storage.get_group(group_id)
    if not group:
        return scim_error_v1(404, f"Group {group_id} not found")
    return format_group_v1(group, request)


@app.post("/scim/v1/Groups", status_code=201)
async def create_group_v1(group_data: GroupRequest, request: Request):
    group = storage.create_group(group_data.model_dump(exclude_none=True))
    return format_group_v1(group, request)


@app.put("/scim/v1/Groups/{group_id}")
async def update_group_v1(group_id: str, group_data: GroupRequest, request: Request):
    if not allows_put_for_groups():
        return scim_error_v1(405, "Method Not Allowed. Use PATCH for group updates.")
    group = storage.update_group(group_id, group_data.model_dump(exclude_none=True))
    if not group:
        return scim_error_v1(404, f"Group {group_id} not found")
    return format_group_v1(group, request)


@app.patch("/scim/v1/Groups/{group_id}")
async def patch_group_v1(group_id: str, patch_data: GroupPatchV1, request: Request):
    if not allows_patch_for_groups():
        return scim_error_v1(405, "Method Not Allowed. Use PUT for group updates.")
    if not patch_data.members:
        return scim_error_v1(400, "No member operations provided")
    operations = [m.model_dump() for m in patch_data.members]
    group = storage.patch_group_members(group_id, operations)
    if not group:
        return scim_error_v1(404, f"Group {group_id} not found")
    return format_group_v1(group, request)


@app.delete("/scim/v1/Groups/{group_id}", status_code=204)
async def delete_group_v1(group_id: str):
    if not storage.delete_group(group_id):
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
    return None


# ============================================================================
# SCIM v2 Users
# ============================================================================


@app.get("/scim/v2/Users")
async def list_users_v2(
    request: Request,
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=0),
    filter: str | None = None,
):
    users, total = storage.list_users(startIndex, count, filter)
    return {
        "schemas": [SCIM_V2_LIST_RESPONSE],
        "totalResults": total,
        "startIndex": startIndex,
        "itemsPerPage": len(users),
        "Resources": [format_user_v2(u, request) for u in users],
    }


@app.get("/scim/v2/Users/{user_id}")
async def get_user_v2(user_id: str, request: Request):
    user = storage.get_user(user_id)
    if not user:
        return scim_error_v2(404, f"User {user_id} not found")
    return format_user_v2(user, request)


@app.post("/scim/v2/Users", status_code=201)
async def create_user_v2(user_data: UserRequest, request: Request):
    if storage.get_user_by_username(user_data.userName):
        return scim_error_v2(409, f"User {user_data.userName} already exists")
    user = storage.create_user(user_data.model_dump(exclude_none=True))
    return format_user_v2(user, request)


@app.put("/scim/v2/Users/{user_id}")
async def update_user_v2(user_id: str, user_data: UserRequest, request: Request):
    user = storage.update_user(user_id, user_data.model_dump(exclude_none=True))
    if not user:
        return scim_error_v2(404, f"User {user_id} not found")
    return format_user_v2(user, request)


@app.delete("/scim/v2/Users/{user_id}", status_code=204)
async def delete_user_v2(user_id: str):
    if not storage.delete_user(user_id):
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return None


# ============================================================================
# SCIM v2 Groups
# ============================================================================


@app.get("/scim/v2/Groups")
async def list_groups_v2(
    request: Request,
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=0),
    filter: str | None = None,
):
    groups, total = storage.list_groups(startIndex, count, filter)
    return {
        "schemas": [SCIM_V2_LIST_RESPONSE],
        "totalResults": total,
        "startIndex": startIndex,
        "itemsPerPage": len(groups),
        "Resources": [format_group_v2(g, request) for g in groups],
    }


@app.get("/scim/v2/Groups/{group_id}")
async def get_group_v2(group_id: str, request: Request):
    group = storage.get_group(group_id)
    if not group:
        return scim_error_v2(404, f"Group {group_id} not found")
    return format_group_v2(group, request)


@app.post("/scim/v2/Groups", status_code=201)
async def create_group_v2(group_data: GroupRequest, request: Request):
    group = storage.create_group(group_data.model_dump(exclude_none=True))
    return format_group_v2(group, request)


@app.put("/scim/v2/Groups/{group_id}")
async def update_group_v2(group_id: str, group_data: GroupRequest, request: Request):
    if not allows_put_for_groups():
        return scim_error_v2(405, "Method Not Allowed. Use PATCH for group updates.")
    group = storage.update_group(group_id, group_data.model_dump(exclude_none=True))
    if not group:
        return scim_error_v2(404, f"Group {group_id} not found")
    return format_group_v2(group, request)


@app.patch("/scim/v2/Groups/{group_id}")
async def patch_group_v2(group_id: str, patch_data: GroupPatchV2, request: Request):
    if not allows_patch_for_groups():
        return scim_error_v2(405, "Method Not Allowed. Use PUT for group updates.")
    if not patch_data.Operations:
        return scim_error_v2(400, "No operations provided")

    operations = []
    for op in patch_data.Operations:
        if op.path == "members" and op.op in ("add", "remove"):
            values = op.value if isinstance(op.value, list) else [op.value] if op.value else []
            for v in values:
                if isinstance(v, dict):
                    operations.append({
                        "value": v.get("value"),
                        "operation": "add" if op.op == "add" else "delete",
                    })

    if not operations:
        return scim_error_v2(400, "No valid member operations found")

    group = storage.patch_group_members(group_id, operations)
    if not group:
        return scim_error_v2(404, f"Group {group_id} not found")
    return format_group_v2(group, request)


@app.delete("/scim/v2/Groups/{group_id}", status_code=204)
async def delete_group_v2(group_id: str):
    if not storage.delete_group(group_id):
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
    return None


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
