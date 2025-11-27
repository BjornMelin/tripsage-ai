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

#### Response Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique session identifier (UUID) |
| `ipAddress` | string | IP address where the session was created |
| `userAgent` | string | User agent string of the session client |
| `createdAt` | string | ISO 8601 timestamp of session creation |
| `lastActivity` | string | ISO 8601 timestamp of last activity |

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

`200 OK`

```json
{
  "totalSessions": 12,
  "activeSessions": 3,
  "loginAttempts": 45,
  "failedLoginAttempts": 2,
  "lastSecurityEvent": "2025-01-20T15:30:00Z"
}
```

#### Response Schema

| Field | Type | Description |
|-------|------|-------------|
| `totalSessions` | number | Total number of sessions |
| `activeSessions` | number | Number of currently active sessions |
| `loginAttempts` | number | Total login attempts in the period |
| `failedLoginAttempts` | number | Number of failed login attempts |
| `lastSecurityEvent` | string | ISO 8601 timestamp of the last security event |

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

### `GET /api/security/events`

Get security events.

**Authentication**: Required
**Rate Limit Key**: `security:events`

#### Response

`200 OK`

```json
[
  {
    "id": "event-uuid",
    "type": "login_attempt",
    "severity": "info",
    "description": "Successful login from 192.168.1.1",
    "timestamp": "2025-01-20T15:30:00Z",
    "ipAddress": "192.168.1.1"
  },
  {
    "id": "event-uuid-2",
    "type": "failed_login",
    "severity": "warning",
    "description": "Failed login attempt: invalid password",
    "timestamp": "2025-01-20T14:25:00Z",
    "ipAddress": "10.0.0.5"
  }
]
```

#### Response Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Event ID (UUID) |
| `type` | string | Event type (login_attempt, failed_login, account_change, permission_change, etc.) |
| `severity` | string | Severity level: `info`, `warning`, `critical` |
| `description` | string | Human-readable event description |
| `timestamp` | string | ISO 8601 timestamp of the event |
| `ipAddress` | string | IP address associated with the event |

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## Dashboard

### `GET /api/dashboard`

Get aggregated dashboard metrics.

**Authentication**: Required
**Rate Limit Key**: `security:dashboard`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `window` | string | No | Time window: `24h`, `7d`, `30d`, `all` (default: `7d`). Note: `window=all` returns aggregated lifetime metrics and may produce large responses; clients should prefer bounded windows or pagination |

#### Response

`200 OK`

```json
{
  "period": "7d",
  "metrics": {
    "totalSessions": 150,
    "activeSessions": 12,
    "loginAttempts": 285,
    "failedLoginAttempts": 8,
    "securityEvents": 42,
    "averageSessionDuration": 3600,
    "topLocations": ["New York", "San Francisco", "London"]
  }
}
```

#### Errors

- `400` - Invalid window parameter
- `401` - Not authenticated
- `429` - Rate limit exceeded
