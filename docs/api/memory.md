# Memory

User memory, context, and conversation history management.

## `POST /api/memory/conversations`

Add conversation memory.

**Authentication**: Required  
**Rate Limit Key**: `memory:conversations`

### Request Body

Conversation memory data including messages and context.

### Response

`200 OK` - Returns memory creation result

### Errors

- `400` - Invalid request
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## `POST /api/memory/search`

Search memories.

**Authentication**: Required  
**Rate Limit Key**: `memory:search`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `limit` | number | No | Maximum results |

### Response

`200 OK` - Returns search results

### Errors

- `400` - Invalid request
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## `GET /api/memory/user/{userId}`

Get user memory data.

**Authentication**: Required  
**Rate Limit Key**: `memory:delete`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userId` | string | Yes | User ID |

### Response

`200 OK` - Returns user memory data

### Errors

- `401` - Not authenticated
- `403` - Cannot access other user's memory
- `429` - Rate limit exceeded

---

## `POST /api/memory/user/{userId}`

Delete all memories for a user.

**Authentication**: Required  
**Rate Limit Key**: `memory:delete`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userId` | string | Yes | User ID |

### Response

`200 OK`

```json
{
  "deleted": true
}
```

### Errors

- `401` - Not authenticated
- `403` - Cannot delete other user's memory
- `429` - Rate limit exceeded

---

## `GET /api/memory/context/{userId}`

Get memory context for a user.

**Authentication**: Required  
**Rate Limit Key**: `memory:context`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userId` | string | Yes | User ID |

### Response

`200 OK`

```json
{
  "context": [...]
}
```

### Errors

- `401` - Not authenticated
- `403` - Cannot access other user's context
- `429` - Rate limit exceeded

---

## `GET /api/memory/stats/{userId}`

Get memory statistics for a user.

**Authentication**: Required  
**Rate Limit Key**: `memory:stats`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userId` | string | Yes | User ID |

### Response

`200 OK` - Returns memory statistics

### Errors

- `401` - Not authenticated
- `403` - Cannot access other user's stats
- `429` - Rate limit exceeded

---

## `GET /api/memory/preferences/{userId}`

Get memory preferences for a user.

**Authentication**: Required  
**Rate Limit Key**: `memory:preferences`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userId` | string | Yes | User ID |

### Response

`200 OK` - Returns memory preferences

### Errors

- `401` - Not authenticated
- `403` - Cannot access other user's preferences
- `429` - Rate limit exceeded

---

## `GET /api/memory/insights/{userId}`

Get memory insights for a user.

**Authentication**: Required  
**Rate Limit Key**: `memory:insights`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userId` | string | Yes | User ID |

### Response

`200 OK` - Returns memory insights

### Errors

- `401` - Not authenticated
- `403` - Cannot access other user's insights
- `429` - Rate limit exceeded
