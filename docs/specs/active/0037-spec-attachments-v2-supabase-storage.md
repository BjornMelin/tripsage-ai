# SPEC-0037: Attachments V2 with Supabase Storage

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-12-10
**Related ADRs**: ADR-0059
**Supersedes**: SPEC-0036

## Overview

This specification defines the API contracts, validation rules, and implementation details for the Attachments V2 system using Supabase Storage for file bytes and Supabase Postgres for metadata persistence.

## Goals

1. Remove runtime dependency on the legacy FastAPI backend for attachments
2. Implement direct file uploads to Supabase Storage from Next.js Route Handlers
3. Use Supabase Postgres for metadata storage with RLS-enforced ownership
4. Provide secure file access via time-limited signed URLs
5. Maintain backward compatibility with existing client code where possible

## Non-Goals

- Client-side direct uploads (future enhancement)
- Complex image transformations (thumbnails, resizing)
- Migration of existing historical attachments (separate effort)
- Virus scanning integration (future enhancement)

## Breaking Changes from SPEC-0036

This specification supersedes SPEC-0036 (Vercel Blob) with the following intentional breaking changes:

1. **Response ID Types**: `tripId` and `chatMessageId` in API responses are now numeric types (integers) rather than stringified values.
   - SPEC-0036: `"tripId": "123"`, `"chatMessageId": "456"` (strings)
   - SPEC-0037: `"tripId": 123, "chatMessageId": 456` (integers)
   - **Client Migration**: Update JSON parsers to handle numeric IDs; typeof checks expecting strings will fail.

2. **Storage Provider**: File bytes now stored in Supabase Storage instead of Vercel Blob.
   - Metadata remains in Supabase Postgres as before.
   - Signed URLs use Supabase endpoints (different domain pattern).

---

## API Contracts

### POST /api/chat/attachments

Upload one or more files to chat attachments storage.

#### Request

**Content-Type**: `multipart/form-data`

**Form Fields**:

- `files` or `files[]`: One or more files uploaded via `multipart/form-data` (e.g., browser File API objects or file uploads from HTTP clients)

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
application/pdf
application/msword
application/vnd.openxmlformats-officedocument.wordprocessingml.document
application/vnd.ms-excel
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
text/csv
```

**Note**: SVG (`image/svg+xml`) is intentionally excluded due to XSS risk (can contain JavaScript).

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
      "url": "https://your-project.supabase.co/storage/v1/object/sign/attachments/chat/user-id/uuid-document.pdf?token=..."
    }
  ],
  "urls": [
    "https://your-project.supabase.co/storage/v1/object/sign/attachments/chat/user-id/uuid-document.pdf?token=..."
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

**400 Bad Request** - MIME type mismatch (magic bytes verification):

```json
{
  "error": "invalid_request",
  "reason": "MIME type mismatch: declared image/jpeg, detected application/pdf"
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
| `tripId` | number | - | Filter by trip ID |
| `chatMessageId` | number | - | Filter by chat message ID |
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
      "name": "file-id-1",
      "originalName": "vacation-photo.jpg",
      "size": 2048000,
      "mimeType": "image/jpeg",
      "url": "https://your-project.supabase.co/storage/v1/object/sign/attachments/chat/user-id/uuid-vacation-photo.jpg?token=...",
      "tripId": 123,
      "chatMessageId": 456,
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

**400 Bad Request** - Invalid query parameters:

```json
{
  "error": "invalid_request",
  "reason": "Invalid query parameters"
}
```

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

### Supabase Storage Configuration

**Bucket**: `attachments` (private)

**Access**: Signed URLs only (no public access)

**Signed URL TTL**: 3600 seconds (1 hour)

### Object Path Scheme

```text
chat/{user_id}/{uuid}-{sanitized_filename}
```

Example:

```text
chat/550e8400-e29b-41d4-a716-446655440000/a1b2c3d4-document.pdf
```

### Metadata Storage (Supabase Postgres)

Uses `file_attachments` table with the following field mappings:

| Field | Source |
|-------|--------|
| `id` | Auto-generated UUID |
| `user_id` | From authenticated session |
| `trip_id` | Optional, from request context |
| `chat_message_id` | Optional, from request context |
| `filename` | Generated UUID (for storage key) |
| `original_filename` | Original file name |
| `file_size` | `file.size` |
| `mime_type` | Detected MIME type (magic bytes verified) |
| `file_path` | Full storage path (e.g., `chat/user-id/uuid-file.jpg`) |
| `bucket_name` | `'attachments'` |
| `upload_status` | `'completed'` after successful upload |

---

## Security Requirements

### 1. Authentication

All endpoints require valid Supabase session via `sb-access-token` cookie.

### 2. Authorization (RLS)

- Table-level: `file_attachments` RLS enforces `auth.uid() = user_id`
- Storage bucket: Policies enforce user can only access paths matching their `user_id`

### 3. MIME Type Verification

Files are verified using magic bytes detection (`file-type` library):

```typescript
import { fileTypeFromBuffer } from 'file-type';

const detected = await fileTypeFromBuffer(buffer);
if (!detected || detected.mime !== declaredType) {
  // Reject: MIME type mismatch
}
```

This prevents attacks where malicious files are disguised as allowed types.

### 4. Filename Sanitization

```typescript
function sanitizeFilename(filename: string): string {
  // Remove path components
  const basename = filename.split(/[/\\]/).pop() ?? filename;

  // Replace special characters
  const sanitized = basename
    .replace(/[<>:"/\\|?*\x00-\x1f]/g, "_")
    .replace(/\s+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_|_$/g, "");

  // Limit length (preserve extension)
  const maxLength = 100;
  if (sanitized.length <= maxLength) {
    return sanitized;
  }

  // Find the last dot that's not the first character (to handle hidden files like .gitignore)
  const lastDotIndex = sanitized.lastIndexOf(".");
  const hasExtension = lastDotIndex > 0;

  if (!hasExtension) {
    // No extension, just truncate to maxLength
    return sanitized.substring(0, maxLength);
  }

  // Split into name and extension (extension includes the leading dot)
  const extension = sanitized.substring(lastDotIndex);
  const name = sanitized.substring(0, lastDotIndex);

  // Calculate space available for the name after reserving space for extension
  const maxNameLength = maxLength - extension.length;

  // If there's no room for even 1 character of name, truncate the whole filename
  if (maxNameLength < 1) {
    return sanitized.substring(0, maxLength);
  }

  // Truncate name and rejoin with extension
  const truncatedName = name.substring(0, maxNameLength);
  return truncatedName + extension;
}
```

### 5. Signed URL Security

All file access requires time-limited signed URLs:

- URLs expire after 1 hour
- Each URL is generated per-request
- No direct public access to storage bucket

### 6. Data Leakage Prevention

- Never return file paths or metadata for other users
- RLS ensures queries are scoped to authenticated user
- Batch signed URL generation validates paths belong to requested files

---

## Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| POST /api/chat/attachments | 10 requests | 1 minute |
| GET /api/attachments/files | 60 requests | 1 minute |

Rate limit keys are derived from `chat:attachments` and `attachments:files` respectively.

### Rate Limiting Implementation

- **Store**: Upstash Redis (distributed); in-memory only for local, single-instance development.
- **Key structure**: `chat:attachments:{userId}:{yyyyMMddHHmm}` (fixed window). Listing route: `attachments:files:{userId}:{yyyyMMddHHmm}`.
- **TTL**: Set expiry equal to window length so counters auto-expire; no manual cleanup required.
- **Distributed requirement**: Use Redis/Upstash in any multi-instance deployment to avoid split-brain counters.
- **Failure mode**: Fail-open with warning telemetry (`rate_limit.backend_error`) and temporarily fall back to conservative in-process limits.

---

## Caching Strategy

### Upload Route (POST)

- No caching (always fresh)
- On success: `revalidateTag('attachments')` and `bumpTag('attachments')` to clear per-user caches in Redis

### Listing Route (GET)

- Per-user Redis cache with 2-minute TTL in Upstash
- Cache key: `attachments:files:{userId}:{normalizedQueryString}`
- Invalidated by upload/delete operations

---

## Telemetry

Span names for observability:

| Operation | Span Name |
|-----------|-----------|
| Upload handler | `chat.attachments.upload` |
| Storage upload | `chat.attachments.storage.upload` |
| Metadata insert | `chat.attachments.metadata.insert` |
| List files | `attachments.files.read` |
| Signed URL generation | `attachments.files.sign` |

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
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/csv',
] as const;

export const ATTACHMENT_MAX_FILE_SIZE = 10 * 1024 * 1024;  // 10MB
export const ATTACHMENT_MAX_FILES = 5;
export const ATTACHMENT_MAX_TOTAL_SIZE = 50 * 1024 * 1024; // 50MB

export const attachmentUploadOptionsSchema = z.strictObject({
  tripId: z.coerce.number().int().nonnegative().optional(),
  chatMessageId: z.coerce.number().int().nonnegative().optional(),
});

export type AttachmentUploadOptions = z.infer<typeof attachmentUploadOptionsSchema>;
```

### List Query Schema

```typescript
export const attachmentListQuerySchema = z.strictObject({
  tripId: z.coerce.number().int().nonnegative().optional(),
  chatMessageId: z.coerce.number().int().nonnegative().optional(),
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
| `name` | Server-generated storage filename (UUID) |
| `originalName` | Client-provided upload filename |
| `size` | File-derived (bytes) |
| `mimeType` | File-derived (magic bytes verified) |
| `url` | Supabase Storage signed URL |
| `tripId` | Client-provided (optional) |
| `chatMessageId` | Client-provided (optional) |
| `uploadStatus` | Server-generated |
| `createdAt` / `updatedAt` | Server-generated timestamps |

```typescript
export const uploadedFileSchema = z.strictObject({
  id: z.uuid(),
  name: z.string(),
  size: z.number().int().nonnegative(),
  status: z.enum(['uploading', 'completed', 'failed']),
  type: z.string(),
  url: z.url().nullable(),
});

export type UploadedFile = z.infer<typeof uploadedFileSchema>;

export const attachmentFileSchema = z.strictObject({
  id: z.uuid(),
  name: z.string(),
  originalName: z.string(),
  size: z.number().int().nonnegative(),
  mimeType: z.string(),
  url: z.url().nullable(),
  tripId: z.number().int().nonnegative().nullable(),
  chatMessageId: z.number().int().nonnegative().nullable(),
  uploadStatus: z.enum(['uploading', 'completed', 'failed']),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

export type AttachmentFile = z.infer<typeof attachmentFileSchema>;

export const paginationSchema = z.strictObject({
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
  hasMore: z.boolean(),
  nextOffset: z.number().int().nonnegative().nullable(),
});

export const attachmentListResponseSchema = z.strictObject({
  items: z.array(attachmentFileSchema),
  pagination: paginationSchema,
});

export type AttachmentListResponse = z.infer<typeof attachmentListResponseSchema>;
```

---

## Implementation Files

| File | Purpose |
|------|---------|
| `src/app/api/chat/attachments/route.ts` | Upload handler |
| `src/app/api/attachments/files/route.ts` | Listing handler |
| `src/domain/schemas/attachments.ts` | Zod v4 validation schemas |
| `src/lib/cache/tags.ts` | Cache tag helpers |
| `src/lib/cache/upstash.ts` | Redis caching utilities |

---

## Testing Requirements

### Unit Tests

1. **Upload Route**:
   - Valid single file upload
   - Valid batch upload (multiple files)
   - Rejection of too-large file
   - Rejection of unsupported MIME type
   - Rejection of too many files
   - MIME type mismatch detection (magic bytes)
   - Missing auth returns 401
   - Storage error handling and cleanup

2. **Listing Route**:
   - List with no filters
   - List filtered by tripId
   - List filtered by chatMessageId
   - Pagination behavior
   - Empty result handling
   - Missing auth returns 401
   - Invalid query parameters return 400

### Integration Tests

1. Upload file via UI → appears in listing
2. Delete file → removed from listing
3. Rate limit enforcement
4. Signed URL expiration handling

---

## Migration / Rollout Phases

### Phase 1 (Current - Implemented)

- Server-side uploads to Supabase Storage
- Supabase metadata storage with RLS
- Magic byte MIME verification
- Per-user listing with signed URLs
- Redis caching for listings

### Phase 2 (Future)

- Client-side uploads for large files
- Progress tracking UI
- Retry logic for failed uploads

### Phase 3 (Future)

- Virus scanning integration
- Thumbnail generation for images
- Full-text search of document contents

---

## References

- ADR-0059: Supabase Storage for Chat Attachments
- Supersedes: SPEC-0036 (Attachments V2 with Vercel Blob)
- SPEC-0017: Attachments Migration Next.js
- Supabase Storage: <https://supabase.com/docs/guides/storage>
- Supabase Storage Access Control: <https://supabase.com/docs/guides/storage/access-control>
- Next.js Cache Revalidation: <https://nextjs.org/docs/app/getting-started/caching-and-revalidating>
- Zod v4 Documentation: <https://zod.dev>
