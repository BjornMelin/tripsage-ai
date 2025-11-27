# Keys (BYOK)

Bring Your Own Key (BYOK) API key management for AI providers.

## `GET /api/keys`

List stored provider API keys (metadata only, no secrets).

**Authentication**: Required
**Rate Limit Key**: `keys:list`

### Response

`200 OK`

```json
[
  {
    "service": "openai",
    "createdAt": "2025-01-15T10:00:00Z",
    "lastUsed": "2025-01-20T15:30:00Z"
  }
]
```

### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## `POST /api/keys`

Upsert a provider API key.

**Authentication**: Required  
**Rate Limit Key**: `keys:create`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `service` | string | Yes | Service name (`openai`, `openrouter`, `anthropic`, `xai`, `gateway`) |
| `apiKey` | string | Yes | API key (max 2048 chars) |
| `baseUrl` | string | No | Gateway base URL (applies to `gateway` service only). Must be HTTPS, with valid resolvable hostname (no wildcards). Required for `gateway` service, optional for self-hosted deployments. Include trailing slash if path-based routing is used. Defaults to public gateway if omitted for `gateway` service. |

### Response

`204 No Content`

### Errors

- `400` - Invalid service or API key format
- `401` - Not authenticated
- `429` - Rate limit exceeded

### Example

```bash
curl -X POST "http://localhost:3000/api/keys" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "service": "openai",
    "apiKey": "sk-..."
  }'
```

---

## `DELETE /api/keys/{service}`

Delete a provider API key.

**Authentication**: Required  
**Rate Limit Key**: `keys:delete`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `service` | string | Yes | Service name (`openai`, `openrouter`, `anthropic`, `xai`, `gateway`) |

### Response

`204 No Content`

### Errors

- `400` - Invalid service
- `401` - Not authenticated
- `404` - Key not found

### Example

```bash
curl -X DELETE "http://localhost:3000/api/keys/openai" \
  --cookie "sb-access-token=$JWT"
```

---

## `POST /api/keys/validate`

Validate a provider API key.

**Authentication**: Required  
**Rate Limit Key**: `keys:validate`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `service` | string | Yes | Service name (`openai`, `openrouter`, `anthropic`, `xai`, `gateway`) |
| `apiKey` | string | Yes | API key to validate |

### Response

`200 OK` (Success)

```json
{
  "valid": true,
  "message": "Key is valid"
}
```

`200 OK` (Failed Validation)

```json
{
  "valid": false,
  "message": "Invalid API key format or authentication failed"
}
```

### Errors

- `400` - Invalid request
- `401` - Not authenticated
- `429` - Rate limit exceeded

### Example

```bash
curl -X POST "http://localhost:3000/api/keys/validate" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "service": "openai",
    "apiKey": "sk-..."
  }'
```
