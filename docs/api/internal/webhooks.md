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

**Example Request:**

```json
{
  "table": "trips",
  "type": "INSERT"
}
```

### Response

`200 OK`

> **Note**: This endpoint returns a simplified response without timestamp for cache invalidation operations.

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
| `bumped` | boolean | Indicates if the cache was invalidated |

### Errors

**Error Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Error type identifier |
| `code` | number | HTTP status code |
| `message` | string | Human-readable error message |

**Error Examples:**

`401 Unauthorized` - Invalid webhook signature

```json
{
  "error": "unauthorized",
  "code": 401,
  "message": "Invalid webhook signature"
}
```

`500 Internal Server Error` - Cache invalidation failed

```json
{
  "error": "internal_server_error",
  "code": 500,
  "message": "Cache invalidation failed"
}
```

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

**Example Request:**

```json
{
  "tripId": "123e4567-e89b-12d3-a456-426614174000",
  "collaboratorUserId": "987fcdeb-51a2-43d7-b123-456789abcdef",
  "eventType": "added",
  "role": "editor",
  "timestamp": "2025-01-20T15:30:00Z"
}
```

### Response

`200 OK`

> **Note**: This endpoint returns processing status with timestamp for tracking event handling.

```json
{
  "ok": true,
  "processed": true,
  "timestamp": "2025-01-20T15:30:00Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | Indicates if the webhook was processed successfully |
| `processed` | boolean | Indicates if the event was processed |
| `timestamp` | string | ISO 8601 timestamp when the event was processed |

### Errors

**Error Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Error type identifier |
| `code` | number | HTTP status code |
| `message` | string | Human-readable error message |

**Error Examples:**

`400 Bad Request` - Invalid webhook payload

```json
{
  "error": "bad_request",
  "code": 400,
  "message": "Invalid webhook payload: missing required field 'tripId'"
}
```

`401 Unauthorized` - Invalid webhook signature

```json
{
  "error": "unauthorized",
  "code": 401,
  "message": "Invalid webhook signature"
}
```

`500 Internal Server Error` - Event processing failed

```json
{
  "error": "internal_server_error",
  "code": 500,
  "message": "Event processing failed"
}
```

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

**Example Request:**

```json
{
  "filePath": "user-uploads/photos/IMG_2024.jpg",
  "eventType": "created",
  "userId": "123e4567-e89b-12d3-a456-426614174000",
  "size": 2048576,
  "mimeType": "image/jpeg",
  "metadata": {
    "bucket": "trip-photos",
    "timestamp": "2025-01-20T15:30:00Z",
    "checksum": "d41d8cd98f00b204e9800998ecf8427e"
  }
}
```

### Response

`200 OK`

> **Note**: This endpoint includes an `indexed` field indicating whether the file was added to the search index.

```json
{
  "ok": true,
  "processed": true,
  "indexed": true,
  "timestamp": "2025-01-20T15:30:00Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | Indicates if the webhook was processed successfully |
| `processed` | boolean | Indicates if the event was processed |
| `indexed` | boolean | Indicates if the file was indexed for search |
| `timestamp` | string | ISO 8601 timestamp when the event was processed |

### Errors

**Error Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Error type identifier |
| `code` | number | HTTP status code |
| `message` | string | Human-readable error message |

**Error Examples:**

`400 Bad Request` - Invalid webhook payload

```json
{
  "error": "bad_request",
  "code": 400,
  "message": "Invalid webhook payload: missing required field 'filePath'"
}
```

`401 Unauthorized` - Invalid webhook signature

```json
{
  "error": "unauthorized",
  "code": 401,
  "message": "Invalid webhook signature"
}
```

`500 Internal Server Error` - Event processing failed

```json
{
  "error": "internal_server_error",
  "code": 500,
  "message": "Event processing failed: unable to index file"
}
```

### Usage

This webhook is triggered when file storage events occur, enabling:

- File indexing and search updates
- Thumbnail generation
- Metadata extraction
