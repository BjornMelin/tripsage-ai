# Webhooks

Webhook endpoints for Postgres real-time database change events.

> **Access**: These endpoints use HMAC signature verification and should only be called by Supabase Postgres triggers via `supabase_functions.http_request`.  
> **Note**: This documentation describes the actual Postgres real-time webhook handlers (Option A: documentation matches implementation). These endpoints receive Postgres change event payloads, not custom webhook formats.

## Authentication

All webhook endpoints require HMAC-SHA256 signature verification:

- **Header**: `X-Signature-HMAC` (hex-encoded HMAC-SHA256 of the raw request body)
- **Secret**: `HMAC_SECRET` environment variable (shared between Supabase and Vercel)
- **Verification**: Signature is computed over the raw request body bytes and compared using timing-safe comparison

Invalid signatures return `401 Unauthorized` with `{error, reason}` response.

## Rate Limiting

Webhook endpoints are **not rate-limited**. They are called by Supabase Postgres triggers and should be trusted once signature verification passes.

---

## `POST /api/hooks/cache`

Cache invalidation webhook for database changes.

**Authentication**: HMAC signature verification (`X-Signature-HMAC` header)  
**Rate Limit**: Not rate-limited

### Request Body

Postgres real-time change event payload:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `table` | string | Yes | Database table name (e.g., `trips`, `trip_collaborators`, `flights`, `accommodations`) |
| `type` | string | Yes | Operation type: `INSERT`, `UPDATE`, or `DELETE` |
| `record` | object \| null | Yes | New record data (null for DELETE operations) |
| `old_record` | object \| null | No | Previous record data (only present for UPDATE/DELETE) |
| `schema` | string | No | Database schema name (defaults to `public`) |
| `occurred_at` | string | No | ISO 8601 timestamp when the change occurred |

**Example Request:**

```json
{
  "table": "trips",
  "type": "INSERT",
  "record": {
    "id": 123,
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Summer Trip"
  },
  "old_record": null,
  "schema": "public",
  "occurred_at": "2025-01-20T15:30:00Z"
}
```

### Response

`200 OK`

```json
{
  "bumped": true,
  "ok": true
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | Indicates if the webhook was processed successfully |
| `bumped` | boolean | Indicates if cache tags were invalidated (version bumped) |

### Errors

**Error Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Error message |

**Error Examples:**

`400 Bad Request` - Invalid payload

```json
{
  "error": "invalid payload"
}
```

`401 Unauthorized` - Invalid webhook signature

```json
{
  "error": "invalid signature or payload"
}
```

### Usage

This webhook is called by Supabase Postgres triggers when database records change. It invalidates relevant cache tags (e.g., `trip`, `user_trips`, `search`) by bumping version counters in Upstash Redis. Supported tables include `trips`, `trip_collaborators`, `flights`, `accommodations`, `search_destinations`, `search_flights`, `search_hotels`, `search_activities`, `chat_messages`, and `chat_sessions`.

---

## `POST /api/hooks/trips`

Trip collaborator webhook for handling `trip_collaborators` table changes.

**Authentication**: HMAC signature verification (`X-Signature-HMAC` header)  
**Rate Limit**: Not rate-limited

### Request Body

Postgres real-time change event payload:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `table` | string | Yes | Database table name (must be `trip_collaborators`) |
| `type` | string | Yes | Operation type: `INSERT`, `UPDATE`, or `DELETE` |
| `record` | object \| null | Yes | New record data (null for DELETE operations) |
| `old_record` | object \| null | No | Previous record data (only present for UPDATE/DELETE) |
| `schema` | string | No | Database schema name (defaults to `public`) |
| `occurred_at` | string | No | ISO 8601 timestamp when the change occurred |

**Example Request:**

```json
{
  "table": "trip_collaborators",
  "type": "INSERT",
  "record": {
    "id": 456,
    "trip_id": 123,
    "user_id": "987fcdeb-51a2-43d7-b123-456789abcdef",
    "role": "editor",
    "created_at": "2025-01-20T15:30:00Z"
  },
  "old_record": null,
  "schema": "public",
  "occurred_at": "2025-01-20T15:30:00Z"
}
```

### Response

`200 OK`

**Success (QStash enqueued):**

```json
{
  "enqueued": true,
  "ok": true
}
```

**Success (fallback processing):**

```json
{
  "enqueued": false,
  "fallback": true,
  "ok": true
}
```

**Skipped (wrong table):**

```json
{
  "ok": true,
  "skipped": true
}
```

**Duplicate (already processed):**

```json
{
  "duplicate": true,
  "ok": true
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | Indicates if the webhook was processed successfully |
| `enqueued` | boolean | Indicates if the event was enqueued to QStash (only present when `true`) |
| `fallback` | boolean | Indicates if fallback in-process processing was used (only present when `true`) |
| `skipped` | boolean | Indicates if the event was skipped due to wrong table (only present when `true`) |
| `duplicate` | boolean | Indicates if the event was a duplicate (only present when `true`) |

### Errors

**Error Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Error type identifier |
| `reason` | string | Human-readable error message |

**Error Examples:**

`401 Unauthorized` - Invalid webhook signature

```json
{
  "error": "invalid_signature",
  "reason": "Invalid signature or payload"
}
```

`500 Internal Server Error` - Database query failed

```json
{
  "error": "db_error",
  "reason": "Supabase query failed"
}
```

### Usage

This webhook is triggered by Supabase Postgres triggers when `trip_collaborators` table changes occur. The handler:

1. Validates the payload and signature
2. Skips events for tables other than `trip_collaborators`
3. Enforces idempotency using Upstash Redis (duplicate events return `{duplicate: true, ok: true}`)
4. Enqueues notification jobs to QStash worker (`/api/jobs/notify-collaborators`) when `QSTASH_TOKEN` is configured
5. Falls back to in-process notification processing if QStash is not available

Events for other tables are silently skipped with `{ok: true, skipped: true}`.

---

## `POST /api/hooks/files`

File attachment webhook for handling `file_attachments` table changes.

**Authentication**: HMAC signature verification (`X-Signature-HMAC` header)  
**Rate Limit**: Not rate-limited

### Request Body

Postgres real-time change event payload:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `table` | string | Yes | Database table name (must be `file_attachments`) |
| `type` | string | Yes | Operation type: `INSERT`, `UPDATE`, or `DELETE` |
| `record` | object \| null | Yes | New record data (null for DELETE operations) |
| `old_record` | object \| null | No | Previous record data (only present for UPDATE/DELETE) |
| `schema` | string | No | Database schema name (defaults to `public`) |
| `occurred_at` | string | No | ISO 8601 timestamp when the change occurred |

**Example Request:**

```json
{
  "table": "file_attachments",
  "type": "INSERT",
  "record": {
    "id": "789abcde-f123-4567-8901-234567890abc",
    "trip_id": 123,
    "file_path": "user-uploads/photos/IMG_2024.jpg",
    "upload_status": "uploading",
    "file_size": 2048576,
    "mime_type": "image/jpeg",
    "created_at": "2025-01-20T15:30:00Z"
  },
  "old_record": null,
  "schema": "public",
  "occurred_at": "2025-01-20T15:30:00Z"
}
```

### Response

`200 OK`

**Success:**

```json
{
  "ok": true
}
```

**Skipped (wrong table):**

```json
{
  "ok": true,
  "skipped": true
}
```

**Duplicate (already processed):**

```json
{
  "duplicate": true,
  "ok": true
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | Indicates if the webhook was processed successfully |
| `skipped` | boolean | Indicates if the event was skipped due to wrong table (only present when `true`) |
| `duplicate` | boolean | Indicates if the event was a duplicate (only present when `true`) |

### Errors

**Error Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Error type identifier or message |

**Error Examples:**

`401 Unauthorized` - Invalid webhook signature

```json
{
  "error": "invalid signature or payload"
}
```

`500 Internal Server Error` - Supabase query failed

```json
{
  "error": "supabase error"
}
```

### Usage

This webhook is triggered by Supabase Postgres triggers when `file_attachments` table changes occur. The handler:

1. Validates the payload and signature
2. Skips events for tables other than `file_attachments`
3. Enforces idempotency using Upstash Redis (duplicate events return `{duplicate: true, ok: true}`)
4. Processes INSERT events with `upload_status: "uploading"` to verify file existence in Supabase Storage

Events for other tables are silently skipped with `{ok: true, skipped: true}`.

---

## Implementation Notes

**Option Chosen**: Option A — Documentation matches the actual Postgres real-time handlers implementation.

These endpoints receive Postgres change event payloads from Supabase triggers, not custom webhook formats. The payload structure follows Supabase's real-time change event format with `table`, `type`, `record`, `old_record`, `schema`, and `occurred_at` fields.

All endpoints:

- Use HMAC-SHA256 signature verification via `X-Signature-HMAC` header
- Are not rate-limited (trusted after signature verification)
- Enforce idempotency using Upstash Redis event keys
- Return standardized success/error responses matching the actual handler implementations
