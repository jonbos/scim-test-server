"""Salesforce-style REST API routes for the mock server."""

import os
import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic

from scim_server.salesforce_storage import sf_storage

# ── Token management ──────────────────────────────────────────────────────

_active_tokens: set[str] = set()

router = APIRouter()

security = HTTPBasic()


def _sf_client_id() -> str:
    return os.environ.get("SF_CLIENT_ID", "")


def _sf_client_secret() -> str:
    return os.environ.get("SF_CLIENT_SECRET", "")


def _verify_bearer(authorization: str = Header(None)):
    """Validate Bearer token on Salesforce data endpoints."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail=[{"message": "Session expired or invalid", "errorCode": "INVALID_SESSION_ID"}],
        )
    token = authorization[7:]
    if token not in _active_tokens:
        raise HTTPException(
            status_code=401,
            detail=[{"message": "Session expired or invalid", "errorCode": "INVALID_SESSION_ID"}],
        )


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


# ── OAuth Token Endpoint ──────────────────────────────────────────────────


@router.post("/services/oauth2/token")
async def oauth_token(request: Request):
    """Issue a Bearer token for client_credentials grant."""
    form = await request.form()
    grant_type = form.get("grant_type", "")
    client_id = form.get("client_id", "")
    client_secret = form.get("client_secret", "")

    if grant_type != "client_credentials":
        return JSONResponse(
            status_code=400,
            content={
                "error": "unsupported_grant_type",
                "error_description": "Only client_credentials is supported",
            },
        )

    expected_id = _sf_client_id()
    expected_secret = _sf_client_secret()

    if not expected_id or not expected_secret:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_client",
                "error_description": "OAuth not configured on server",
            },
        )

    id_ok = secrets.compare_digest(str(client_id), expected_id)
    secret_ok = secrets.compare_digest(str(client_secret), expected_secret)

    if not (id_ok and secret_ok):
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_client", "error_description": "Invalid client credentials"},
        )

    token = str(uuid.uuid4())
    _active_tokens.add(token)

    return {
        "access_token": token,
        "instance_url": _base_url(request),
        "token_type": "Bearer",
    }


# ── User Endpoints ────────────────────────────────────────────────────────


@router.post(
    "/services/data/v62.0/sobjects/User",
    status_code=201,
    dependencies=[Depends(_verify_bearer)],
)
async def create_user(request: Request):
    body = await request.json()
    user = sf_storage.create_user(body)
    return {"Id": user["Id"], "success": True, "errors": []}


@router.get(
    "/services/data/v62.0/sobjects/User/{user_id}",
    dependencies=[Depends(_verify_bearer)],
)
async def get_user(user_id: str):
    user = sf_storage.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=[{
                "message": f"Not found: {user_id}",
                "errorCode": "NOT_FOUND",
            }],
        )
    return user


@router.patch(
    "/services/data/v62.0/sobjects/User/{user_id}",
    status_code=204,
    dependencies=[Depends(_verify_bearer)],
)
async def update_user(user_id: str, request: Request):
    body = await request.json()
    if not sf_storage.update_user(user_id, body):
        raise HTTPException(
            status_code=404,
            detail=[{"message": f"entity is deleted: {user_id}", "errorCode": "ENTITY_IS_DELETED"}],
        )
    return None


@router.delete(
    "/services/data/v62.0/sobjects/User/{user_id}",
    status_code=204,
    dependencies=[Depends(_verify_bearer)],
)
async def delete_user(user_id: str):
    if not sf_storage.delete_user(user_id):
        raise HTTPException(
            status_code=404,
            detail=[{"message": f"entity is deleted: {user_id}", "errorCode": "ENTITY_IS_DELETED"}],
        )
    return None


@router.get(
    "/services/data/v62.0/sobjects/User",
    dependencies=[Depends(_verify_bearer)],
)
async def list_users(request: Request):
    records = sf_storage.list_users()
    return sf_storage.paginate(records, _base_url(request))


# ── PermissionSet Endpoints ───────────────────────────────────────────────


@router.post(
    "/services/data/v62.0/sobjects/PermissionSet",
    status_code=201,
    dependencies=[Depends(_verify_bearer)],
)
async def create_permission_set(request: Request):
    body = await request.json()
    pset = sf_storage.create_permission_set(body)
    return {"Id": pset["Id"], "success": True, "errors": []}


@router.get(
    "/services/data/v62.0/sobjects/PermissionSet/{ps_id}",
    dependencies=[Depends(_verify_bearer)],
)
async def get_permission_set(ps_id: str):
    pset = sf_storage.get_permission_set(ps_id)
    if not pset:
        raise HTTPException(
            status_code=404,
            detail=[{
                "message": f"Not found: {ps_id}",
                "errorCode": "NOT_FOUND",
            }],
        )
    return pset


@router.patch(
    "/services/data/v62.0/sobjects/PermissionSet/{ps_id}",
    status_code=204,
    dependencies=[Depends(_verify_bearer)],
)
async def update_permission_set(ps_id: str, request: Request):
    body = await request.json()
    if not sf_storage.update_permission_set(ps_id, body):
        raise HTTPException(
            status_code=404,
            detail=[{"message": f"entity is deleted: {ps_id}", "errorCode": "ENTITY_IS_DELETED"}],
        )
    return None


@router.delete(
    "/services/data/v62.0/sobjects/PermissionSet/{ps_id}",
    status_code=204,
    dependencies=[Depends(_verify_bearer)],
)
async def delete_permission_set(ps_id: str):
    if not sf_storage.delete_permission_set(ps_id):
        raise HTTPException(
            status_code=404,
            detail=[{"message": f"entity is deleted: {ps_id}", "errorCode": "ENTITY_IS_DELETED"}],
        )
    return None


@router.get(
    "/services/data/v62.0/sobjects/PermissionSet",
    dependencies=[Depends(_verify_bearer)],
)
async def list_permission_sets(request: Request):
    records = sf_storage.list_permission_sets()
    return sf_storage.paginate(records, _base_url(request))


# ── PermissionSetAssignment Endpoints ─────────────────────────────────────


@router.post(
    "/services/data/v62.0/sobjects/PermissionSetAssignment",
    status_code=201,
    dependencies=[Depends(_verify_bearer)],
)
async def create_assignment(request: Request):
    body = await request.json()
    assignment = sf_storage.create_assignment(body)
    return {"Id": assignment["Id"], "success": True, "errors": []}


@router.delete(
    "/services/data/v62.0/sobjects/PermissionSetAssignment/{assignment_id}",
    status_code=204,
    dependencies=[Depends(_verify_bearer)],
)
async def delete_assignment(assignment_id: str):
    if not sf_storage.delete_assignment(assignment_id):
        raise HTTPException(
            status_code=404,
            detail=[{
                "message": f"entity is deleted: {assignment_id}",
                "errorCode": "ENTITY_IS_DELETED",
            }],
        )
    return None


# ── Pagination Endpoint ──────────────────────────────────────────────────


@router.get(
    "/services/data/v62.0/query/{page_id}",
    dependencies=[Depends(_verify_bearer)],
)
async def next_page(page_id: str, request: Request):
    result = sf_storage.get_next_page(page_id, _base_url(request))
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=[{
                "message": f"query locator has expired: {page_id}",
                "errorCode": "INVALID_QUERY_LOCATOR",
            }],
        )
    return result


# ── Admin Endpoints (Basic Auth protected via main app) ──────────────────


@router.delete("/admin/salesforce/clear")
async def clear_salesforce():
    """Clear all Salesforce data and tokens."""
    sf_storage.clear()
    _active_tokens.clear()
    return {"message": "All Salesforce data cleared"}


@router.get("/admin/salesforce/status")
async def salesforce_status():
    """Get Salesforce data counts."""
    return {
        "users": len(sf_storage.users),
        "permission_sets": len(sf_storage.permission_sets),
        "assignments": len(sf_storage.assignments),
    }
