# Webhooks

Webhook endpoints for database and file event handling.

> **Access**: These endpoints use webhook signature verification and should only be called by Supabase.

## `POST /api/hooks/cache`

Cache invalidation webhook for database changes.

**Authentication**: Webhook signature verification  
**Rate Limit Key**: Not rate-limited

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `table` | string | Yes | Database table name |
| `type` | string | Yes | Operation type (`INSERT`, `UPDATE`, `DELETE`) |

### Response

`200 OK`

```json
{
  "bumped": true,
  "ok": true
}
```

### Errors

- `401` - Invalid webhook signature
- `500` - Cache invalidation failed

### Usage

This webhook is called by Supabase when database records change. It invalidates the relevant cache keys to ensure data consistency.

---

## `POST /api/hooks/trips`

Trip collaborators webhook for handling trip sharing events.

**Authentication**: Webhook signature verification
**Rate Limit Key**: `trips:webhook`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tripId` | string | Yes | Trip ID (UUID) |
| `collaboratorUserId` | string | Yes | Collaborator user ID (UUID) |
| `eventType` | string | Yes | Event type: `added`, `removed`, `role_changed` |
| `role` | string | No | Collaborator role when `eventType` is `role_changed` (e.g., "editor", "viewer") |
| `timestamp` | string | No | ISO 8601 timestamp of the event |

### Response

`200 OK`

```json
{
  "ok": true,
  "processed": true,
  "timestamp": "2025-01-20T15:30:00Z"
}
```

### Errors

- `400` - Invalid webhook payload
- `401` - Invalid webhook signature
- `500` - Event processing failed

### Usage

This webhook is triggered when trip collaboration events occur, such as:

- Adding a collaborator to a trip
- Removing a collaborator from a trip
- Changing a collaborator's role

---

## `POST /api/hooks/files`

File webhook for handling file storage events.

**Authentication**: Webhook signature verification
**Rate Limit Key**: `files:webhook`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filePath` | string | Yes | Full file path in storage |
| `eventType` | string | Yes | Event type: `created`, `updated`, `deleted` |
| `userId` | string | Yes | User ID who triggered the event |
| `size` | number | No | File size in bytes (for created/updated events) |
| `mimeType` | string | No | MIME type of the file (for created/updated events) |
| `metadata` | object | No | Additional metadata {bucket, timestamp, checksum} |

### Response

`200 OK`

```json
{
  "ok": true,
  "processed": true,
  "indexed": true,
  "timestamp": "2025-01-20T15:30:00Z"
}
```

### Errors

- `400` - Invalid webhook payload
- `401` - Invalid webhook signature
- `500` - Event processing failed

### Usage

This webhook is triggered when file storage events occur, enabling:

- File indexing and search updates
- Thumbnail generation
- Metadata extraction
