# SCIM Enterprise Extension: 1.1 vs 2.0 Differences

Scraped/verified: 2026-02-24. Sources: draft-scim-core-schema-01 and RFC 7643 Section 4.3.

---

## Schema URNs

| Version | URN |
|---------|-----|
| SCIM 1.1 | `urn:scim:schemas:extension:enterprise:1.0` |
| SCIM 2.0 | `urn:ietf:params:scim:schemas:extension:enterprise:2.0:User` |

Both versions embed extension fields under the URN key in the resource JSON body.

---

## Top-Level Fields (identical in both versions)

| Field | Type | Notes |
|-------|------|-------|
| `employeeNumber` | String | Same name, same semantics |
| `costCenter` | String | Same name, same semantics |
| `organization` | String | Same name, same semantics |
| `division` | String | Same name, same semantics |
| `department` | String | Same name, same semantics |
| `manager` | Complex | Sub-attributes differ — see below |

No fields are added or removed between versions at the top level. Only `manager` sub-attributes differ.

---

## Manager Sub-Attributes

This is the **only structural difference** requiring separate models.

| Sub-attribute | SCIM 1.1 | SCIM 2.0 | Notes |
|---------------|----------|----------|-------|
| `managerId` | String (REQUIRED if present) | **ABSENT** | Replaced by `value` in 2.0 |
| `value` | **ABSENT** | String (RECOMMENDED) | Carries the `id` of the manager's User resource |
| `$ref` | **ABSENT** | URI String (RECOMMENDED) | Relative or absolute URI to the manager's User resource |
| `displayName` | String (READ-ONLY, OPTIONAL) | String (READ-ONLY, OPTIONAL) | Identical semantics |

### SCIM 1.1 manager example

```json
"manager": {
  "managerId": "26118915-6090-4610-87e4-49d8ca9f808d",
  "displayName": "John Smith"
}
```

### SCIM 2.0 manager example

```json
"manager": {
  "value": "26118915-6090-4610-87e4-49d8ca9f808d",
  "$ref": "../Users/26118915-6090-4610-87e4-49d8ca9f808d",
  "displayName": "John Smith"
}
```

---

## Impact on Python Models

Two separate Manager models are needed. The shared enterprise fields (`employeeNumber` through `department`) can use a base class or be duplicated.

```python
class ManagerV1(BaseModel):
    managerId: str | None = None      # SCIM 1.1: id of manager's User resource
    displayName: str | None = None    # READ-ONLY

class ManagerV2(BaseModel):
    value: str | None = None          # SCIM 2.0: id of manager's User resource
    ref: str | None = Field(default=None, alias="$ref")  # URI
    displayName: str | None = None    # READ-ONLY

    model_config = {"populate_by_name": True}

class EnterpriseUserV1(BaseModel):
    employeeNumber: str | None = None
    costCenter: str | None = None
    organization: str | None = None
    division: str | None = None
    department: str | None = None
    manager: ManagerV1 | None = None

class EnterpriseUserV2(BaseModel):
    employeeNumber: str | None = None
    costCenter: str | None = None
    organization: str | None = None
    division: str | None = None
    department: str | None = None
    manager: ManagerV2 | None = None
```

Note on `$ref`: Pydantic cannot use `$ref` as a Python field name directly. Use `Field(alias="$ref")` with `model_config = {"populate_by_name": True}` and serialize with `by_alias=True`.

---

## Other Version Differences (non-enterprise)

These apply to the core User schema but do NOT affect the enterprise extension models:

| Difference | SCIM 1.1 | SCIM 2.0 |
|------------|----------|----------|
| PATCH format | Attribute-level merge; `operation: "delete"` on multi-value items | `Operations` array with `op`/`path`/`value` (RFC 7644) |
| Filter syntax | Basic `eq`, `co`, `sw`, `pr`, `gt`, `ge`, `lt`, `le`, `and`, `or`, `not` | Same operators, adds `ne`; same syntax — largely compatible |
| `$ref` in Group members | Not present | Added to `members` sub-attributes |
| Error response format | Informal | `urn:ietf:params:scim:api:messages:2.0:Error` schema defined |
| Bulk operations | Not defined | RFC 7644 Section 3.7 |
| ServiceProviderConfig | Basic | Extended with `bulk`, `filter`, `changePassword`, etc. |

The core User attributes (all singular fields, multi-value attribute names and sub-attributes) are **identical** between 1.1 and 2.0. Separate v1/v2 User models are NOT required for the core schema — only for PATCH handling and enterprise manager.

---

## Sources

- [RFC 7643 Section 4.3 — Enterprise User Extension](https://www.rfc-editor.org/rfc/rfc7643#section-4.3) — scraped 2026-02-24
- [RFC 7643 Section 8.3 — Enterprise User Example](https://www.rfc-editor.org/rfc/rfc7643#section-8.3) — scraped 2026-02-24
- [draft-scim-core-schema-01 Section 7 — Enterprise User](https://datatracker.ietf.org/doc/html/draft-scim-core-schema-01#section-7) — scraped 2026-02-24
