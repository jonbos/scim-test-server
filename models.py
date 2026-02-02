"""Pydantic models for SCIM requests and responses."""

from pydantic import BaseModel, Field


class Name(BaseModel):
    formatted: str | None = None
    familyName: str | None = None
    givenName: str | None = None
    middleName: str | None = None
    honorificPrefix: str | None = None
    honorificSuffix: str | None = None


class Email(BaseModel):
    value: str
    type: str | None = None
    primary: bool | None = None


class Member(BaseModel):
    value: str
    display: str | None = None
    type: str | None = "User"


class UserRequest(BaseModel):
    userName: str
    name: Name | None = None
    displayName: str | None = None
    emails: list[Email] | None = None
    active: bool = True
    externalId: str | None = None


class GroupRequest(BaseModel):
    displayName: str
    members: list[Member] | None = None
    externalId: str | None = None


class SeedUser(BaseModel):
    userName: str
    name: Name | None = None
    displayName: str | None = None
    emails: list[Email] | None = None
    active: bool = True
    externalId: str | None = None


class SeedGroup(BaseModel):
    displayName: str
    members: list[str] | None = Field(
        default=None, description="List of userNames to add as members"
    )
    externalId: str | None = None


class SeedData(BaseModel):
    users: list[SeedUser] | None = None
    groups: list[SeedGroup] | None = None


class MemberPatchOperation(BaseModel):
    """SCIM 1.1 member patch operation."""

    value: str
    operation: str = "add"


class GroupPatchV1(BaseModel):
    """SCIM 1.1 group patch request."""

    schemas: list[str] | None = None
    members: list[MemberPatchOperation] | None = None


class PatchOperation(BaseModel):
    """SCIM 2.0 patch operation."""

    op: str
    path: str | None = None
    value: list[dict] | dict | str | None = None


class GroupPatchV2(BaseModel):
    """SCIM 2.0 group patch request."""

    schemas: list[str] | None = None
    Operations: list[PatchOperation] | None = None
