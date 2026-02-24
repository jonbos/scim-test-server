"""Pydantic models for SCIM requests and responses."""

from typing import Any

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


class PhoneNumber(BaseModel):
    value: str
    type: str | None = None
    primary: bool | None = None
    display: str | None = None


class InstantMessaging(BaseModel):
    value: str
    type: str | None = None
    primary: bool | None = None
    display: str | None = None


class Photo(BaseModel):
    value: str
    type: str | None = None
    primary: bool | None = None
    display: str | None = None


class Address(BaseModel):
    formatted: str | None = None
    streetAddress: str | None = None
    locality: str | None = None
    region: str | None = None
    postalCode: str | None = None
    country: str | None = None
    type: str | None = None
    primary: bool | None = None


class GroupMembership(BaseModel):
    value: str
    display: str | None = None
    type: str | None = None


class Entitlement(BaseModel):
    value: str
    type: str | None = None
    primary: bool | None = None
    display: str | None = None


class Role(BaseModel):
    value: str
    type: str | None = None
    primary: bool | None = None
    display: str | None = None


class X509Certificate(BaseModel):
    value: str
    type: str | None = None
    primary: bool | None = None
    display: str | None = None


class ManagerV1(BaseModel):
    """SCIM 1.1 manager (draft-scim-core-schema §7)."""

    managerId: str | None = None
    displayName: str | None = None


class ManagerV2(BaseModel):
    """SCIM 2.0 manager (RFC 7643 §4.3)."""

    value: str | None = None
    ref: str | None = Field(default=None, alias="$ref")
    displayName: str | None = None

    model_config = {"populate_by_name": True}


class EnterpriseUserV1(BaseModel):
    """SCIM 1.1 enterprise extension (urn:scim:schemas:extension:enterprise:1.0)."""

    employeeNumber: str | None = None
    costCenter: str | None = None
    organization: str | None = None
    division: str | None = None
    department: str | None = None
    manager: ManagerV1 | None = None


class EnterpriseUserV2(BaseModel):
    """SCIM 2.0 enterprise extension (RFC 7643 §4.3)."""

    employeeNumber: str | None = None
    costCenter: str | None = None
    organization: str | None = None
    division: str | None = None
    department: str | None = None
    manager: ManagerV2 | None = None


# URN keys for enterprise extension
ENTERPRISE_URN_V1 = "urn:scim:schemas:extension:enterprise:1.0"
ENTERPRISE_URN_V2 = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"


class Member(BaseModel):
    value: str
    display: str | None = None
    type: str | None = "User"


class UserRequest(BaseModel):
    userName: str
    name: Name | None = None
    displayName: str | None = None
    nickName: str | None = None
    profileUrl: str | None = None
    title: str | None = None
    userType: str | None = None
    preferredLanguage: str | None = None
    locale: str | None = None
    timezone: str | None = None
    password: str | None = None
    emails: list[Email] | None = None
    phoneNumbers: list[PhoneNumber] | None = None
    ims: list[InstantMessaging] | None = None
    photos: list[Photo] | None = None
    addresses: list[Address] | None = None
    entitlements: list[Entitlement] | None = None
    roles: list[Role] | None = None
    x509Certificates: list[X509Certificate] | None = None
    active: bool = True
    externalId: str | None = None

    # Enterprise extension — accepted under either v1 or v2 URN key
    model_config = {"populate_by_name": True}

    # We accept both URN keys via __pydantic_extra__; see validator below
    # Store as a plain dict so we can forward it to storage
    enterprise_extension: EnterpriseUserV1 | EnterpriseUserV2 | None = Field(
        default=None, exclude=True
    )

    def model_post_init(self, __context):
        """Extract enterprise extension from either URN key."""
        super().model_post_init(__context)
        # Pydantic extra fields aren't enabled, so we rely on callers
        # providing the extension via the from_request classmethod or
        # directly in the dict passed to storage.


class GroupRequest(BaseModel):
    displayName: str
    members: list[Member] | None = None
    externalId: str | None = None


class SeedUser(BaseModel):
    userName: str
    name: Name | None = None
    displayName: str | None = None
    nickName: str | None = None
    profileUrl: str | None = None
    title: str | None = None
    userType: str | None = None
    preferredLanguage: str | None = None
    locale: str | None = None
    timezone: str | None = None
    password: str | None = None
    emails: list[Email] | None = None
    phoneNumbers: list[PhoneNumber] | None = None
    ims: list[InstantMessaging] | None = None
    photos: list[Photo] | None = None
    addresses: list[Address] | None = None
    entitlements: list[Entitlement] | None = None
    roles: list[Role] | None = None
    x509Certificates: list[X509Certificate] | None = None
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
    value: Any = None


class GroupPatchV2(BaseModel):
    """SCIM 2.0 group patch request."""

    schemas: list[str] | None = None
    Operations: list[PatchOperation] | None = None


class UserPatchV1(BaseModel):
    """SCIM 1.1 user patch request.

    Supports partial updates to user attributes.
    For setting active=false (disable-on-delete), use: {"active": false}
    """

    schemas: list[str] | None = None
    userName: str | None = None
    name: Name | None = None
    displayName: str | None = None
    nickName: str | None = None
    profileUrl: str | None = None
    title: str | None = None
    userType: str | None = None
    preferredLanguage: str | None = None
    locale: str | None = None
    timezone: str | None = None
    password: str | None = None
    emails: list[Email] | None = None
    phoneNumbers: list[PhoneNumber] | None = None
    ims: list[InstantMessaging] | None = None
    photos: list[Photo] | None = None
    addresses: list[Address] | None = None
    entitlements: list[Entitlement] | None = None
    roles: list[Role] | None = None
    x509Certificates: list[X509Certificate] | None = None
    active: bool | None = None
    externalId: str | None = None


class UserPatchV2(BaseModel):
    """SCIM 2.0 user patch request using Operations array."""

    schemas: list[str] | None = None
    Operations: list[PatchOperation] | None = None
