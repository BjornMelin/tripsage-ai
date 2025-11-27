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

### Request Body

Trip collaborator event data including:

- Trip ID
- Collaborator user ID
- Event type (added, removed, role changed)

### Response

`200 OK`

### Errors

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

### Request Body

File event data including:

- File path
- Event type (created, deleted, updated)
- File metadata

### Response

`200 OK`

### Errors

- `401` - Invalid webhook signature
- `500` - Event processing failed

### Usage

This webhook is triggered when file storage events occur, enabling:

- File indexing and search updates
- Thumbnail generation
- Metadata extraction
