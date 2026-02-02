# SCIM Test Server

A Python FastAPI server supporting SCIM 1.1 and 2.0 protocols with configurable behavior modes. Designed for integration testing of SCIM connectors.

## Quick Start

```bash
docker pull ghcr.io/jonbos/scim-test-server:latest
docker run -p 8000:8000 ghcr.io/jonbos/scim-test-server:latest
```

## Configuration

Configuration uses a **presets + overrides** model:
- **Presets** define a base configuration for common scenarios
- **Overrides** allow fine-grained control over individual settings
- Precedence: Runtime overrides > Env var overrides > Preset defaults

### Presets

| Preset | groups_put | groups_patch | Description |
|--------|------------|--------------|-------------|
| `permissive` (default) | true | true | Accepts both methods |
| `pingdirectory` | false | true | Simulates PingDirectory behavior |
| `put_only` | true | false | Legacy mode, no PATCH support |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SCIM_PRESET` | Base preset (permissive, pingdirectory, put_only) |
| `SCIM_GROUPS_PUT` | Override: allow PUT for groups (true/false) |
| `SCIM_GROUPS_PATCH` | Override: allow PATCH for groups (true/false) |

### Examples

**Use a preset:**
```bash
docker run -e SCIM_PRESET=pingdirectory -p 8000:8000 ghcr.io/jonbos/scim-test-server:latest
```

**Preset with override:**
```bash
# PingDirectory preset but also disable PATCH
docker run -e SCIM_PRESET=pingdirectory -e SCIM_GROUPS_PATCH=false -p 8000:8000 ghcr.io/jonbos/scim-test-server:latest
```

**Runtime configuration via API:**
```bash
# Change preset
curl -X PUT http://localhost:8000/admin/preset/pingdirectory

# Set individual override
curl -X PUT "http://localhost:8000/admin/config/groups_put?value=false"

# Clear an override (revert to preset default)
curl -X DELETE http://localhost:8000/admin/config/groups_put

# View current configuration
curl http://localhost:8000/admin/config
```

## Endpoints

### Admin
| Path | Method | Description |
|------|--------|-------------|
| `/admin/seed` | POST | Seed users/groups from JSON |
| `/admin/clear` | DELETE | Clear all data |
| `/admin/status` | GET | User/group counts and configuration |
| `/admin/config` | GET | View current configuration |
| `/admin/preset/{preset}` | PUT | Change active preset (clears overrides) |
| `/admin/config/{setting}` | PUT | Set a configuration override |
| `/admin/config/{setting}` | DELETE | Clear an override (revert to preset) |

### SCIM 1.1
- `GET/POST /scim/v1/Users`
- `GET/PUT/DELETE /scim/v1/Users/{id}`
- `GET/POST /scim/v1/Groups`
- `GET/PUT/PATCH/DELETE /scim/v1/Groups/{id}`

### SCIM 2.0
- `GET/POST /scim/v2/Users`
- `GET/PUT/DELETE /scim/v2/Users/{id}`
- `GET/POST /scim/v2/Groups`
- `GET/PUT/PATCH/DELETE /scim/v2/Groups/{id}`

## Seeding Data

```bash
curl -X POST http://localhost:8000/admin/seed \
  -H "Content-Type: application/json" \
  -d @seed_data.json
```

Example `seed_data.json`:
```json
{
  "users": [
    {"userName": "jdoe", "email": "jdoe@example.com", "displayName": "John Doe"}
  ],
  "groups": [
    {"displayName": "Engineering", "members": []}
  ]
}
```

## Local Development

```bash
pip install fastapi uvicorn pydantic
uvicorn main:app --reload
```
