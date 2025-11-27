# Security

Security sessions, metrics, events, and dashboard.

## Sessions

### `GET /api/security/sessions`

List active sessions for authenticated user.

**Authentication**: Required  
**Rate Limit Key**: `security:sessions:list`

#### Response

`200 OK`

```json
[
  {
    "id": "session-uuid",
    "ipAddress": "192.168.1.1",
    "userAgent": "Mozilla/5.0...",
    "createdAt": "2025-01-15T10:00:00Z",
    "lastActivity": "2025-01-20T15:30:00Z"
  }
]
```

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

### `DELETE /api/security/sessions/{sessionId}`

Terminate a specific session.

**Authentication**: Required  
**Rate Limit Key**: `security:sessions:terminate`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sessionId` | string | Yes | Session ID |

#### Response

`204 No Content`

#### Errors

- `401` - Not authenticated
- `404` - Session not found
- `429` - Rate limit exceeded

---

## Metrics & Events

### `GET /api/security/metrics`

Get security metrics.

**Authentication**: Required  
**Rate Limit Key**: `security:metrics`

#### Response

`200 OK` - Returns security metrics

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

### `GET /api/security/events`

Get security events.

**Authentication**: Required  
**Rate Limit Key**: `security:events`

#### Response

`200 OK` - Returns security events

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## Dashboard

### `GET /api/dashboard`

Get aggregated dashboard metrics.

**Authentication**: Required  
**Rate Limit Key**: `dashboard:metrics`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `window` | string | No | Time window (`24h`, `7d`, `30d`, `all`, default: `7d`) |

#### Response

`200 OK` - Returns dashboard metrics

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded
