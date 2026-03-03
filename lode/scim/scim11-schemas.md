# SCIM 1.1 Core Schemas

Authoritative attribute reference for `draft-scim-core-schema-01`.
Scraped: 2026-02-24.

## Schema URNs

| Resource | Schema URN |
|----------|-----------|
| User | `urn:scim:schemas:core:1.0` |
| Group | `urn:scim:schemas:core:1.0` |
| Enterprise User extension | `urn:scim:schemas:extension:enterprise:1.0` |

---

## Common Attributes (all resources)

Defined in Section 5.1. Present on every resource.

| Attribute | Type | Required | Mutability | Notes |
|-----------|------|----------|-----------|-------|
| `id` | String | Yes | READ-ONLY | Service Provider–assigned unique identifier |
| `externalId` | String | No | Mutable (consumer-issued) | Client-assigned opaque identifier |
| `schemas` | String[] | Yes | READ-ONLY | Array of schema URNs |
| `meta` | Complex | No | READ-ONLY | Resource metadata |

**meta sub-attributes** (all READ-ONLY):

| Sub-attribute | Type | Notes |
|---------------|------|-------|
| `created` | DateTime | When resource was added |
| `lastModified` | DateTime | Time of last update |
| `location` | URI | Canonical URI of the resource |
| `version` | String | Matches ETag header value |
| `attributes` | String[] | Names of attributes to remove during PATCH |

---

## User Schema (`urn:scim:schemas:core:1.0`)

Defined in Section 6.

### Singular Attributes

| Attribute | Type | Required | Mutability | Notes |
|-----------|------|----------|-----------|-------|
| `userName` | String | **Yes** | Mutable | Unique; used for direct authentication |
| `name` | Complex | No | Mutable | See sub-attributes below |
| `displayName` | String | No | Mutable | Name suitable for display to end-users |
| `nickName` | String | No | Mutable | Casual name |
| `profileUrl` | URI | No | Mutable | Fully qualified URL to online profile |
| `title` | String | No | Mutable | Job title (e.g., "Vice President") |
| `userType` | String | No | Mutable | Org-to-user relationship (e.g., "Employee", "Contractor") |
| `preferredLanguage` | String | No | Mutable | ISO 639-1 with optional ISO 3166-1 country (e.g., `en_US`) |
| `locale` | String | No | Mutable | Default location for localization |
| `timezone` | String | No | Mutable | Olson timezone DB format (e.g., `America/Los_Angeles`) |
| `active` | Boolean | No | Mutable | `true` means user can log in |
| `password` | String | No | Mutable | Clear-text; **MUST NEVER be returned** by provider |

**name sub-attributes** (all String, all Mutable, all Optional):

| Sub-attribute | Notes |
|---------------|-------|
| `formatted` | Full name including titles and suffixes |
| `familyName` | Last name |
| `givenName` | First name |
| `middleName` | Middle name |
| `honorificPrefix` | e.g., "Ms.", "Dr." |
| `honorificSuffix` | e.g., "Jr.", "III" |

### Multi-valued Attributes

All multi-valued items support these standard sub-attributes unless noted:
- `value` — the primary value
- `type` — canonical type string (see per-attribute canonical values)
- `primary` — Boolean; at most ONE entry may be `true` per attribute
- `display` — READ-ONLY, human-readable label
- `operation` — for PATCH only; only valid value is `"delete"`

#### emails

Canonical `type` values: `work`, `home`, `other`

#### phoneNumbers

Canonical `type` values: `work`, `home`, `mobile`, `fax`, `pager`, `other`
Values SHOULD be canonicalized per RFC 3966.

#### ims

Instant messaging addresses.
Canonical `type` values: `aim`, `gtalk`, `icq`, `xmpp`, `msn`, `skype`, `qq`, `yahoo`

#### photos

URLs pointing to image files (not web pages containing images).
Canonical `type` values: `photo`, `thumbnail`

#### addresses

Physical mailing addresses. Sub-attributes:

| Sub-attribute | Type | Notes |
|---------------|------|-------|
| `formatted` | String | Full address, formatted for display |
| `streetAddress` | String | Street address, may include apartment/suite |
| `locality` | String | City or locality |
| `region` | String | State or region |
| `postalCode` | String | Zip or postal code |
| `country` | String | ISO 3166-1 alpha-2 (e.g., `US`) |
| `type` | String | Canonical: `work`, `home`, `other` |
| `primary` | Boolean | At most one `true` allowed |

#### groups (READ-ONLY)

List of groups the user belongs to. Sub-attributes:

| Sub-attribute | Type | Mutability | Notes |
|---------------|------|-----------|-------|
| `value` | String | READ-ONLY | `id` of the Group resource |
| `display` | String | READ-ONLY | Group's display name |
| `type` | String | READ-ONLY | Canonical: `direct`, `indirect` |

Group membership **MUST** be changed via the Group resource, not this attribute.

#### entitlements

Things the user "has". No canonical types defined.

#### roles

Roles the user "is" (e.g., `Student`, `Faculty`). No canonical types defined.

#### x509Certificates

DER-encoded x509 certificates, base64-encoded in `value`. No canonical types defined.

---

## Group Schema (`urn:scim:schemas:core:1.0`)

Defined in Section 8.

### Singular Attributes

| Attribute | Type | Required | Mutability |
|-----------|------|----------|-----------|
| `id` | String | Yes | READ-ONLY |
| `displayName` | String | **Yes** | Mutable |
| `externalId` | String | No | Mutable (consumer-issued) |
| `schemas` | String[] | Yes | READ-ONLY |
| `meta` | Complex | No | READ-ONLY |

### Multi-valued Attributes

#### members

| Sub-attribute | Type | Required | Mutability | Notes |
|---------------|------|----------|-----------|-------|
| `value` | String | Yes | Mutable | `id` of the member resource |
| `display` | String | No | READ-ONLY | Display name of the member |
| `type` | String | No | READ-ONLY | Canonical: `User`, `Group` |

PATCH for member add (SCIM 1.1 style):
```json
{
  "schemas": ["urn:scim:schemas:core:1.0"],
  "members": [{"value": "<user-id>", "operation": "add"}]
}
```

PATCH for member delete:
```json
{
  "schemas": ["urn:scim:schemas:core:1.0"],
  "members": [{"value": "<user-id>", "operation": "delete"}]
}
```

---

## Enterprise User Extension (`urn:scim:schemas:extension:enterprise:1.0`)

Used in addition to `urn:scim:schemas:core:1.0` when present. Include both URNs in `schemas`.

| Attribute | Type | Required | Mutability | Notes |
|-----------|------|----------|-----------|-------|
| `employeeNumber` | String | No | Mutable | Numeric or alphanumeric, based on hire order |
| `costCenter` | String | No | Mutable | Cost center name |
| `organization` | String | No | Mutable | Organization name |
| `division` | String | No | Mutable | Division name |
| `department` | String | No | Mutable | Department name |
| `manager` | Complex | No | Mutable | See sub-attributes below |

**manager sub-attributes:**

| Sub-attribute | Type | Required | Mutability |
|---------------|------|----------|-----------|
| `managerId` | String | **Yes** (if manager present) | Mutable | `id` of the manager's SCIM User resource |
| `displayName` | String | No | READ-ONLY | Manager's display name |

Example User with Enterprise Extension:
```json
{
  "schemas": [
    "urn:scim:schemas:core:1.0",
    "urn:scim:schemas:extension:enterprise:1.0"
  ],
  "userName": "bjensen",
  "urn:scim:schemas:extension:enterprise:1.0": {
    "employeeNumber": "701984",
    "costCenter": "4130",
    "organization": "Acme",
    "division": "Theme Park",
    "department": "Tour Operations",
    "manager": {
      "managerId": "26118915-6090-4610-87e4-49d8ca9f808d",
      "displayName": "John Smith"
    }
  }
}
```

---

## What This Server Currently Implements

`src/scim_server/models.py` implements a subset:

**UserRequest** covers: `userName`, `name` (full), `displayName`, `emails`, `active`, `externalId`
**GroupRequest** covers: `displayName`, `members` (with `value`, `display`, `type`), `externalId`

**Missing from current models** (not implemented, spec-defined):
- `nickName`, `profileUrl`, `title`, `userType`, `preferredLanguage`, `locale`, `timezone`, `password`
- `phoneNumbers`, `ims`, `photos`, `addresses`, `groups` (read-only membership list)
- `entitlements`, `roles`, `x509Certificates`
- Enterprise User extension

---

## SCIM 2.0 Enterprise Extension Comparison

For full comparison including model requirements, see `lode/scim/enterprise-extension-diff.md`.

**Quick summary of manager differences:**

| Field | SCIM 1.1 | SCIM 2.0 |
|-------|----------|----------|
| Manager user id | `managerId` (String, REQUIRED if manager present) | `value` (String, RECOMMENDED) |
| Manager URI | not present | `$ref` (URI String, RECOMMENDED) |
| Display name | `displayName` (READ-ONLY) | `displayName` (READ-ONLY) |

The SCIM 2.0 Enterprise User adds `$ref` and renames `managerId` → `value`. All other enterprise fields (`employeeNumber`, `costCenter`, `organization`, `division`, `department`) are identical in name and semantics across both versions.

---

## Sources

- [draft-scim-core-schema-01 (IETF Datatracker)](https://datatracker.ietf.org/doc/html/draft-scim-core-schema-01) — scraped 2026-02-24
- [scim.cloud spec mirror](https://scim.cloud/specs/draft-scim-core-schema-01.html) — scraped 2026-02-24
- [RFC 7643 Section 4.3](https://www.rfc-editor.org/rfc/rfc7643#section-4.3) — scraped 2026-02-24
- [RFC 7643 Section 8.3 (examples)](https://www.rfc-editor.org/rfc/rfc7643#section-8.3) — scraped 2026-02-24
