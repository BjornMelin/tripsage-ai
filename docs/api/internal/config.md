# Agent Configuration

Admin-only endpoints for managing AI agent configurations.

> **Access**: These endpoints require admin authentication.

## `GET /api/config/agents/{agentType}`

Get agent configuration.

**Authentication**: Required (Admin only)  
**Rate Limit Key**: `config:agents:read`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agentType` | string | Yes | Agent type (`flightAgent`, `accommodationAgent`, `destinationAgent`, `itineraryAgent`, `budgetAgent`, `memoryAgent`, `routerAgent`) |

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scope` | string | No | Configuration scope (default: "global") |

### Response

`200 OK`

```json
{
  "agentType": "flightAgent",
  "scope": "global",
  "config": {
    "model": "gpt-4",
    "temperature": 0.7,
    "maxTokens": 2048,
    "topP": 0.95,
    "timeoutSeconds": 30,
    "description": "Flight search agent configuration"
  },
  "versionId": "version-uuid",
  "createdAt": "2025-01-15T10:00:00Z",
  "updatedAt": "2025-01-20T15:30:00Z"
}
```

### Errors

- `401` - Not authenticated
- `403` - Admin access required
- `404` - Configuration not found
- `429` - Rate limit exceeded

---

## `PUT /api/config/agents/{agentType}`

Update agent configuration.

**Authentication**: Required (Admin only)  
**Rate Limit Key**: `config:agents:update`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agentType` | string | Yes | Agent type |

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scope` | string | No | Configuration scope (default: "global") |

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | No | Model name |
| `temperature` | number | No | Temperature (0-2) |
| `maxTokens` | number | No | Maximum tokens |
| `topP` | number | No | Top P |
| `timeoutSeconds` | number | No | Timeout in seconds |
| `description` | string | No | Configuration description |

### Response

`200 OK`

```json
{
  "agentType": "flightAgent",
  "scope": "global",
  "config": {
    "model": "gpt-4",
    "temperature": 0.7,
    "maxTokens": 2048,
    "topP": 0.95,
    "timeoutSeconds": 30,
    "description": "Flight search agent configuration"
  },
  "versionId": "version-uuid",
  "createdAt": "2025-01-15T10:00:00Z",
  "updatedAt": "2025-01-20T15:30:00Z"
}
```

### Errors

- `400` - Validation failed
- `401` - Not authenticated
- `403` - Admin access required
- `429` - Rate limit exceeded

---

## `GET /api/config/agents/{agentType}/versions`

List agent configuration versions.

**Authentication**: Required (Admin only)  
**Rate Limit Key**: `config:agents:versions`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agentType` | string | Yes | Agent type |

### Response

`200 OK`

```json
{
  "items": [
    {
      "versionId": "version-uuid-1",
      "createdAt": "2025-01-20T15:30:00Z",
      "description": "Updated temperature to 0.7",
      "config": {
        "model": "gpt-4",
        "temperature": 0.7
      }
    },
    {
      "versionId": "version-uuid-2",
      "createdAt": "2025-01-15T10:00:00Z",
      "description": "Initial configuration",
      "config": {
        "model": "gpt-4",
        "temperature": 0.5
      }
    }
  ],
  "page": 1,
  "pageSize": 20,
  "totalCount": 2
}
```

### Errors

- `401` - Not authenticated
- `403` - Admin access required
- `429` - Rate limit exceeded

---

## `POST /api/config/agents/{agentType}/rollback/{versionId}`

Rollback agent configuration to a previous version.

**Authentication**: Required (Admin only)
**Rate Limit Key**: `config:agents:rollback`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agentType` | string | Yes | Agent type |
| `versionId` | string | Yes | Version ID to rollback to |

### Response

`200 OK`

```json
{
  "rolledBackToVersionId": "version-uuid-2",
  "previousVersionId": "version-uuid-1",
  "timestamp": "2025-01-20T15:35:00Z",
  "config": {
    "model": "gpt-4",
    "temperature": 0.5,
    "maxTokens": 2048,
    "topP": 0.95,
    "timeoutSeconds": 30
  }
}
```

### Errors

- `401` - Not authenticated
- `403` - Admin access required
- `404` - Version not found
- `429` - Rate limit exceeded
