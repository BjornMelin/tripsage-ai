# Security

Security sessions, metrics, events, and dashboard.

## MFA Recovery Endpoints (auth)

| Endpoint | Purpose | Auth | Additional Requirements |
| --- | --- | --- | --- |
| `POST /api/auth/mfa/backup/verify` | Consume a backup code | Authenticated | Rate limit `auth:mfa:backup:verify`; returns `error: "invalid_backup_code"` (400) for invalid codes and `error: "internal_error"` (500) on server faults |
| `POST /api/auth/mfa/backup/regenerate` | Regenerate backup codes | Authenticated | AAL2 required; rate limit `auth:mfa:backup:regenerate`; returns `error: "mfa_required"` (403) when step-up MFA is not satisfied; writes audit trail |

Environment prerequisites:

- Set `MFA_BACKUP_CODE_PEPPER` (>=16 chars) for backup-code hashing in all environments (local `.env.local`, CI secrets, deployment secret manager).
- Configure `SUPABASE_JWT_SECRET` (>=16 chars) as the Supabase JWT signing key.
- Backup-code hashing prefers `MFA_BACKUP_CODE_PEPPER`; when it is unset, the system derives a pepper from `SUPABASE_JWT_SECRET` for bootstrap/startup compatibility. This fallback is **not** recommended for long-term use because rotating the JWT secret invalidates all existing backup codes.
- Operators should treat `MFA_BACKUP_CODE_PEPPER` and `SUPABASE_JWT_SECRET` as distinct secrets: the pepper is only for deterministic backup-code hashing/salting, while the JWT secret is for token signing.

Audit events for backup-code operations are stored in the `mfa_backup_code_audit` table (schema in `supabase/migrations/20251122000000_base_schema.sql`) with columns:

- `id` (UUID, PK)
- `user_id` (UUID)
- `event` (`"regenerated"` or `"consumed"`)
- `count` (integer)
- `ip` (text)
- `user_agent` (text)
- `created_at` (timestamptz)

### MFA audit trail: PII handling and retention

`mfa_backup_code_audit` contains PII-bearing fields (`ip`, `user_agent`). Recommended handling:

- **Retention policy**: configure a retention window (for example, 90–180 days) and periodically purge older records via database TTL jobs or scheduled cleanup.
- **Anonymization / redaction**:
  - Store truncated or hashed IP addresses for long-term retention (for example, keep full IP for 7–30 days, then hash or mask octets).
  - Normalize or strip user-agent strings to coarse categories (browser, OS, device) instead of raw strings where possible.
- **Access controls**:
  - Restrict direct table access to service roles and a small set of security/ops roles via RLS and Supabase role grants.
  - Expose audit data through dedicated endpoints or dashboards with least-privilege defaults.
- **Audit logging**:
  - Log every access to audit records (who accessed what and when) through OpenTelemetry spans and structured application logs.
  - Integrate high-risk events (e.g., bulk export of audit rows) with your alerting system (PagerDuty, Slack).
- **Compliance**:
  - Align retention/anonymization with GDPR/CCPA and similar regulations (e.g., data minimization and storage limitation).
  - Provide mechanisms to support data subject requests by locating and, where permitted, deleting or anonymizing records related to a given user.

### `POST /api/auth/mfa/backup/verify`

Consume a single backup code for the authenticated user.

**Authentication**: Required  
**Rate Limit Key**: `auth:mfa:backup:verify`

#### Request Body

```json
{
  "code": "ABCDE-12345"
}
```

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `code` | string | Yes | Backup code in `AAAAA-12345` format (validated with strict casing and length). |

#### Successful Response

`200 OK`

```json
{
  "data": {
    "remaining": 9,
    "success": true
  }
}
```

| Field | Type | Description |
| ----- | ---- | ----------- |
| `remaining` | number | Number of unused backup codes left for the user. |
| `success` | boolean | Always `true` for a successful verification. |

#### Errors

- `400` – Invalid payload or backup code format/content; response shape: `{ "error": "invalid_backup_code" }`.
- `401` – Not authenticated.
- `429` – Rate limit exceeded for `auth:mfa:backup:verify`.
- `500` – Internal server error; response shape: `{ "error": "internal_error" }`.

### `POST /api/auth/mfa/backup/regenerate`

Regenerate a new set of backup codes for the authenticated user and invalidate existing codes.

**Authentication**: Required  
**Rate Limit Key**: `auth:mfa:backup:regenerate`  
**Additional requirement**: Step-up MFA (AAL2) via `requireAal2()`; when not satisfied, the endpoint returns `403` with `error: "mfa_required"`.

#### Request Body

```json
{
  "count": 10
}
```

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `count` | number | No | Number of backup codes to generate (1–20). Defaults to 10 when omitted. |

#### Successful Response

`200 OK`

```json
{
  "data": {
    "backupCodes": ["ABCDE-12345", "FGHIJ-67890"]
  }
}
```

| Field | Type | Description |
| ----- | ---- | ----------- |
| `backupCodes` | string[] | List of newly generated backup codes. Previous codes are invalidated. |

#### Errors

- `401` – Not authenticated.
- `403` – Step-up MFA not satisfied; response shape: `{ "error": "mfa_required" }`.
- `429` – Rate limit exceeded for `auth:mfa:backup:regenerate`.
- `500` – Internal server error during regeneration; response shape: `{ "error": "backup_regenerate_failed" }`.

## Sessions

### `GET /api/security/sessions`

List active sessions for authenticated user.

**Authentication**: Required
**Rate Limit Key**: `security:sessions:list`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | number | No | Page number for pagination (default: `1`) |
| `limit` | number | No | Results per page (default: `20`, max: `100`) |

**Note**: Use pagination parameters (`page`, `limit`) for bounded queries. Avoid unbounded requests for large session histories. Server enforces maximum limits to prevent excessive memory usage.

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

- `400` - Invalid pagination parameters (e.g., invalid page or limit values)
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

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `window` | string | No | Time window: `24h`, `7d`, `30d` (default: `7d`) |

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

- `400` - Invalid window parameter (must be `24h`, `7d`, or `30d`)
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

### `GET /api/security/events`

Get security events.

**Authentication**: Required
**Rate Limit Key**: `security:events`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | number | No | Page number for pagination (default: `1`) |
| `limit` | number | No | Results per page (default: `20`, max: `100`) |

**Note**: Use pagination parameters (`page`, `limit`) for bounded queries. Avoid unbounded requests for large event histories. Server enforces maximum limits to prevent excessive memory usage.

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

**PII Handling Notice**: The `ipAddress` field may contain Personally Identifiable Information (PII) depending on jurisdiction and regulatory requirements (GDPR, CCPA, etc.). Recommended handling includes:

- **Retention Policy**: Implement TTL configuration for automatic expiration of IP address data after a defined period (e.g., 90 days)
- **Anonymization**: Consider partial redaction (e.g., `192.168.xxx.xxx`) or hashing for long-term storage
- **Access Controls**: Apply RBAC restrictions to endpoints exposing IP addresses; limit access to security administrators only
- **Audit Logging**: Maintain audit trails for all access to PII fields with user ID, timestamp, and purpose
- **Compliance**: Ensure handling aligns with applicable data protection regulations (GDPR Article 6, CCPA Section 1798.100)
- **Configuration**: Provide optional toggle to disable or mask IP addresses in API responses (`EXPOSE_FULL_IP_ADDRESSES=false`)

#### Errors

- `400` - Invalid pagination parameters (e.g., invalid page or limit values)
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
