# SPEC-0036: Attachments V2 with Vercel Blob

**Version**: 1.0.0
**Status**: Implementing
**Date**: 2025-12-10
**Related ADRs**: ADR-0058

## Overview

This specification defines the API contracts, validation rules, and implementation details for the Attachments V2 system using Vercel Blob for file storage and Supabase for metadata persistence.

## Goals

1. Remove runtime dependency on the legacy FastAPI backend for attachments
2. Implement direct file uploads to Vercel Blob from Next.js Route Handlers
3. Use Supabase for metadata storage with RLS-enforced ownership
4. Maintain backward compatibility with existing client code where possible

## Non-Goals

- Client-side direct uploads (future enhancement)
- Complex image transformations (thumbnails, resizing)
- Migration of existing historical attachments (separate effort)
- Virus scanning integration (future enhancement)

---

## API Contracts

### POST /api/chat/attachments

Upload one or more files to chat attachments storage.

#### Request

**Content-Type**: `multipart/form-data`

**Form Fields**:

- `files` or `files[]`: One or more `File` objects

**Headers**:

- `Cookie`: Must include valid Supabase session (`sb-access-token`)
- `Content-Length`: Must not exceed 50MB total

#### Validation Rules

| Rule | Limit | Error Code |
|------|-------|------------|
| Max files per request | 5 | `invalid_request` |
| Max file size | 10MB | `invalid_request` |
| Max total payload | 50MB | `invalid_request` |
| Allowed MIME types | See below | `invalid_request` |
| Auth required | Yes | `unauthenticated` |

**Allowed MIME Types**:

```text
image/jpeg
image/png
image/gif
image/webp
image/svg+xml
application/pdf
application/msword
application/vnd.openxmlformats-officedocument.wordprocessingml.document
application/vnd.ms-excel
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
text/csv
```

#### Success Response (200 OK)

```json
{
  "files": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "document.pdf",
      "size": 1024000,
      "type": "application/pdf",
      "status": "completed",
      "url": "https://xyz.public.blob.vercel-storage.com/chat/user-id/uuid-document.pdf"
    }
  ],
  "urls": [
    "https://xyz.public.blob.vercel-storage.com/chat/user-id/uuid-document.pdf"
  ]
}
```

#### Error Responses

**400 Bad Request** - Invalid content type:

```json
{
  "error": "invalid_request",
  "reason": "Invalid content type"
}
```

**400 Bad Request** - No files:

```json
{
  "error": "invalid_request",
  "reason": "No files uploaded"
}
```

**400 Bad Request** - Too many files:

```json
{
  "error": "invalid_request",
  "reason": "Maximum 5 files allowed per request"
}
```

**400 Bad Request** - File too large:

```json
{
  "error": "invalid_request",
  "reason": "File \"video.mp4\" exceeds maximum size of 10MB"
}
```

**400 Bad Request** - Invalid MIME type:

```json
{
  "error": "invalid_request",
  "reason": "File \"script.exe\" has invalid type. Allowed types: image/jpeg, image/png, ..."
}
```

**401 Unauthorized**:

```json
{
  "error": "unauthenticated",
  "reason": "Missing authenticated session"
}
```

**413 Payload Too Large**:

```json
{
  "error": "invalid_request",
  "reason": "Request payload exceeds maximum total size of 50MB"
}
```

**429 Too Many Requests** (Rate limited):

```json
{
  "error": "rate_limited",
  "reason": "Too many requests",
  "retryAfter": 60
}
```

**500 Internal Server Error**:

```json
{
  "error": "internal",
  "reason": "File upload failed"
}
```

---

### GET /api/attachments/files

List attachment files for the authenticated user with optional filters.

#### Request (Query Parameters)

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tripId` | BigInt (stringified) | - | Filter by trip ID |
| `chatMessageId` | BigInt (stringified) | - | Filter by chat message ID |
| `limit` | number | 20 | Max items per page (1-100) |
| `offset` | number | 0 | Pagination offset |

**Headers**:

- `Cookie`: Must include valid Supabase session

#### Success Response (200 OK) - GET

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "vacation-photo.jpg",
      "originalName": "vacation-photo.jpg",
      "size": 2048000,
      "mimeType": "image/jpeg",
      "url": "https://xyz.public.blob.vercel-storage.com/chat/user-id/uuid-vacation-photo.jpg",
      "tripId": "123",
      "chatMessageId": "987654321012345678",
      "uploadStatus": "completed",
      "createdAt": "2025-12-10T10:30:00Z",
      "updatedAt": "2025-12-10T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 42,
    "limit": 20,
    "offset": 0,
    "hasMore": true,
    "nextOffset": 20
  }
}
```

#### Error Responses (GET)

**401 Unauthorized**:

```json
{
  "error": "unauthenticated",
  "reason": "Missing authenticated session"
}
```

**429 Too Many Requests** (Rate limited):

```json
{
  "error": "rate_limited",
  "reason": "Too many requests",
  "retryAfter": 60
}
```

---

## Storage Architecture

### Vercel Blob Configuration

**Environment Variables**:

```bash
# Required in production
BLOB_READ_WRITE_TOKEN=vercel_blob_rw_xxx

# Optional: Custom public domain
BLOB_PUBLIC_BASE_URL=https://attachments.tripsage.ai
```

### Object Path Scheme

```text
chat/{user_id}/{uuid}-{sanitized_filename}
```

Example:

```text
chat/550e8400-e29b-41d4-a716-446655440000/a1b2c3d4-document.pdf
```

### Metadata Storage (Supabase)

Uses existing `file_attachments` table with the following field mappings:

| Field | Source |
|-------|--------|
| `id` | Auto-generated UUID |
| `user_id` | From authenticated session |
| `trip_id` | Optional, from request context |
| `chat_message_id` | Optional, from request context |
| `filename` | Generated UUID (for storage key) |
| `original_filename` | Original file name |
| `file_size` | `file.size` |
| `mime_type` | `file.type` |
| `file_path` | `blob.pathname` from Vercel Blob response |
| `bucket_name` | `'vercel_blob'` |
| `upload_status` | `'completed'` after successful upload |

---

## Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| POST /api/chat/attachments | 10 requests | 1 minute |
| GET /api/attachments/files | 60 requests | 1 minute |

Rate limit keys are derived from `chat:attachments` and `attachments:files` respectively.

### Rate Limiting Implementation

- **Store**: Upstash Redis (distributed); in-memory only for local single-instance development.
- **Key structure**: `chat:attachments:{userId|apiKey}:{yyyyMMddHHmm}` (fixed window) or `chat:attachments:{userId|apiKey}` (token bucket). Listing route: `attachments:files:{userId}:{yyyyMMddHHmm}`.
- **TTL**: Set expiry equal to window length so counters auto-expire; no manual cleanup required.
- **Distributed requirement**: Use Redis/Upstash in any multi-instance deployment to avoid split-brain counters.
- **Failure mode**: Fail-open with warning telemetry (`rate_limit.backend_error`) and temporarily fall back to conservative in-process limits; escalate via alerts when backend unavailable.

---

## Caching Strategy

### Upload Route (POST)

- No caching (always fresh)
- On success: `revalidateTag('attachments')` and `bumpTag('attachments')` to clear per-user caches in Redis

### Listing Route (GET)

- Per-user Redis cache with 2-minute TTL in Upstash
- Cache key: `attachments:files:{userId}:{queryString}`
- Invalidated by upload/delete operations

---

## Security Requirements

1. **Authentication**: All endpoints require valid Supabase session
2. **Authorization**: RLS policies enforce user-level access control
3. **Filename Sanitization**: Strip path components, limit length, escape special chars
4. **MIME Type Validation**: Validate both declared type and magic bytes (future enhancement)
5. **Size Limits**: Enforced at route handler level before upload
6. **Data Leakage**: Never return blob path/metadata for another user; rely on RLS and userId-scoped queries.
7. **Public URLs**: Prefer signed or expiring URLs for sensitive data; current public URLs rely on obscurity plus RLS for metadata access.

---

## Telemetry

Span names for observability:

| Operation | Span Name |
|-----------|-----------|
| Upload | `chat.attachments.upload` |
| Blob PUT | `chat.attachments.blob.put` |
| Metadata Insert | `chat.attachments.metadata.insert` |
| List Files | `attachments.files.read` |

---

## Migration / Rollout Phases

### Phase 1 (Current)

- Server-side uploads to Vercel Blob
- Supabase metadata storage
- Basic validation (size, type, count)
- Per-user listing from Supabase

### Phase 2 (Future)

- Client-side uploads for large files
- Progress tracking UI
- Retry logic for failed uploads

### Phase 3 (Future)

- Virus scanning integration
- Thumbnail generation for images
- Full-text search of document contents

---

## Validation Schemas (Zod v4)

### Upload Options Schema

```typescript
import { z } from 'zod';

export const ATTACHMENT_ALLOWED_MIME_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'image/svg+xml',
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/csv',
] as const;

export const attachmentUploadOptionsSchema = z.strictObject({
  tripId: z
    .string()
    .regex(/^\d+$/, { error: "tripId must be a numeric string" })
    .optional(),
  chatMessageId: z
    .string()
    .regex(/^\d+$/, { error: "chatMessageId must be a numeric string" })
    .optional(),
});

export type AttachmentUploadOptions = z.infer<typeof attachmentUploadOptionsSchema>;
```

### List Query Schema

```typescript
export const attachmentListQuerySchema = z.strictObject({
  tripId: z
    .string()
    .regex(/^\d+$/, { error: "tripId must be a numeric string" })
    .optional(),
  chatMessageId: z
    .string()
    .regex(/^\d+$/, { error: "chatMessageId must be a numeric string" })
    .optional(),
  limit: z.coerce.number().int().min(1).max(100).default(20),
  offset: z.coerce.number().int().min(0).default(0),
});

export type AttachmentListQuery = z.infer<typeof attachmentListQuerySchema>;
```

### Response Schemas

Field sources for response objects:

| Field | Source |
|-------|--------|
| `id` | Server-generated UUID |
| `name` | Server-generated storage filename |
| `originalName` | Client-provided upload filename |
| `size` | File-derived (bytes) |
| `mimeType` | File-derived (from upload) |
| `url` | File-derived (Vercel Blob URL) |
| `tripId` | Client-provided BigInt ID serialized as string (optional) |
| `chatMessageId` | Client-provided BigInt ID serialized as string (optional) |
| `uploadStatus` | Server-generated |
| `createdAt` / `updatedAt` | Server-generated timestamps |

```typescript
export const attachmentFileSchema = z.strictObject({
  id: z.uuid(),
  name: z.string(),
  originalName: z.string(),
  size: z.number().int().nonnegative(),
  mimeType: z.string(),
  url: z.url(),
  tripId: z
    .string()
    .regex(/^\d+$/, { error: "tripId must be a numeric string" })
    .nullable(),
  chatMessageId: z
    .string()
    .regex(/^\d+$/, { error: "chatMessageId must be a numeric string" })
    .nullable(),
  uploadStatus: z.enum(['uploading', 'completed', 'failed']),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export type AttachmentFile = z.infer<typeof attachmentFileSchema>;

export const attachmentListResponseSchema = z.strictObject({
  items: z.array(attachmentFileSchema),
  pagination: z.strictObject({
    total: z.number().int().nonnegative(),
    limit: z.number().int().positive(),
    offset: z.number().int().nonnegative(),
    hasMore: z.boolean(),
    nextOffset: z.number().int().nonnegative().nullable(),
  }),
});

export type AttachmentListResponse = z.infer<typeof attachmentListResponseSchema>;
```

### Example Request/Response

```jsonc
// Upload request (multipart/form-data)
// Fields: file=<binary>; tripId=123; chatMessageId=987654321012345678

// Successful upload response body
{
  "files": [
    {
      "id": "0c8b9e18-7d7c-4d50-a9f5-4b9d52c9c27a",
      "name": "0c8b9e18-7d7c-4d50-a9f5-4b9d52c9c27a-itinerary.pdf",
      "originalName": "itinerary.pdf",
      "size": 524288,
      "mimeType": "application/pdf",
      "url": "https://attachments.tripsage.ai/chat/user-id/0c8b9e18-7d7c-4d50-a9f5-4b9d52c9c27a-itinerary.pdf",
      "tripId": "123",
      "chatMessageId": "987654321012345678",
      "uploadStatus": "completed",
      "createdAt": "2025-12-10T10:30:00Z",
      "updatedAt": "2025-12-10T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 20,
    "offset": 0,
    "hasMore": false,
    "nextOffset": null
  }
}
```

---

## Testing Requirements

### Unit Tests

1. **Upload Route**:
   - Valid single file upload
   - Valid batch upload (multiple files)
   - Rejection of too-large file
   - Rejection of unsupported MIME type
   - Rejection of too many files
   - Missing auth returns 401

2. **Listing Route**:
   - List with no filters
   - List filtered by tripId
   - Pagination behavior
   - Empty result handling
   - Missing auth returns 401

### Integration Tests

1. Upload file via UI → appears in listing
2. Delete file → removed from listing
3. Rate limit enforcement

---

## References

- ADR-0058: Vercel Blob for Chat Attachments Storage
- SPEC-0017: Attachments Migration Next.js
- Vercel Blob Server Upload: <https://vercel.com/docs/storage/vercel-blob/server-upload>
- Vercel Blob Client Upload: <https://vercel.com/docs/vercel-blob/client-upload>
- Next.js Cache Revalidation: <https://nextjs.org/docs/app/getting-started/caching-and-revalidating>
- Zod v4 Documentation: <https://zod.dev>
