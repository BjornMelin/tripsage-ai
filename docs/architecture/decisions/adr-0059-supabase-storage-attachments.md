# ADR-0059: Supabase Storage for Chat Attachments

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-12-10
**Category**: Architecture/Storage
**Domain**: Attachments, File Storage
**Related ADRs**: ADR-0058 (superseded), ADR-0040
**Related Specs**: SPEC-0017, SPEC-0037

## Context

The TripSage application previously handled chat attachments through a proxy architecture where Next.js Route Handlers forwarded requests to a legacy FastAPI backend. During the migration to a frontend-only Next.js deployment, we evaluated storage options including Vercel Blob (documented in ADR-0058) and Supabase Storage.

### Original Proposal (ADR-0058)

ADR-0058 proposed using Vercel Blob for file bytes with Supabase for metadata only. This approach was reconsidered during implementation due to:

1. **Security Model Mismatch**: Vercel Blob uses public URLs with obscurity (random suffixes) rather than true access control. This creates potential security concerns for user-uploaded files.

2. **Authentication Complexity**: Vercel Blob requires separate token management (`BLOB_READ_WRITE_TOKEN`) whereas Supabase Storage integrates directly with existing Supabase authentication.

3. **RLS Integration**: Supabase Storage bucket policies integrate natively with Row-Level Security, enabling consistent access control across storage and metadata.

4. **Signed URL Security**: Supabase Storage provides time-limited signed URLs, ensuring files are only accessible to authenticated users with valid sessions.

## Decision

We will use **Supabase Storage** for both file bytes and metadata storage, replacing the Vercel Blob approach documented in ADR-0058.

### Storage Architecture

1. **Supabase Storage** for file bytes:
   - Private bucket named `attachments`
   - Server-side uploads via `supabase.storage.from("attachments").upload()`
   - Signed URLs via `createSignedUrl()` / `createSignedUrls()` for secure access
   - 1-hour URL expiration for download links

2. **Supabase Postgres** for metadata:
   - Existing `file_attachments` table stores ownership, file metadata, and storage paths
   - RLS policies enforce user-level access control
   - Enables filtering by `trip_id`, `chat_message_id`, `user_id`

3. **Chat attachments first**: Begin with chat attachments; extend to trip images and avatars in subsequent phases.

### Object Path Scheme

Attachment paths follow a deterministic scheme:

```text
chat/{user_id}/{uuid}-{sanitized_filename}
```

- `{user_id}` is the authenticated user's UUID
- `{uuid}` is a cryptographically secure random UUID for uniqueness
- `{sanitized_filename}` preserves original name for human readability

Example:

```text
chat/550e8400-e29b-41d4-a716-446655440000/a1b2c3d4-vacation-photo.jpg
```

### Security Implementation

1. **MIME Type Verification**: Files are validated using magic byte detection (`file-type` library) to prevent MIME spoofing attacks. Declared MIME types must match detected types.

2. **Filename Sanitization**: Path components stripped, length limited to 100 characters, special characters escaped.

3. **Signed URLs**: All file access requires time-limited signed URLs (1-hour expiry). No public URLs exposed.

4. **RLS Policies**: Storage bucket policies enforce that users can only access their own files or files shared via trip collaboration.

### Implementation Approach

1. **Server-side uploads**: Use `supabase.storage.from("attachments").upload()` with validated content type
2. **Metadata persistence**: Insert into `file_attachments` after successful storage upload
3. **Validation**: Zod v4 schemas enforce size limits (10MB per file), MIME types, and file counts (max 5)
4. **Cache invalidation**: Use `revalidateTag('attachments')` and Upstash `bumpTag()` for listing cache

#### Signed URL TTL and Refresh Strategy

Signed URLs expire after 1 hour. For long-lived references (pages open beyond the TTL), implement the following:

**Client-side detection**:

- Handle 403/410 responses when accessing expired signed URLs
- Detect via HTTP status codes or explicit error response from storage
- Example: `if (response.status === 403 || response.status === 410) { /* URL expired */ }`

**Server-side refresh endpoint**:

- Implement `GET /api/attachments/{id}/refresh-url` to regenerate signed URLs on demand
- Validates user ownership before issuing new URL
- Returns new signed URL with fresh 1-hour TTL
- Example response: `{ "url": "https://...", "expiresAt": "2025-12-10T23:00:00Z" }`

**Error handling for batch operations**:

- When listing files with URLs, batch regenerate any expired URLs via `createSignedUrls()`
- Validate paths belong to authenticated user before signing
- Stale URLs are acceptable; refresh on access failure
- Example: User opens attachment list after 45+ minutes; URLs are pre-emptively refreshed on response

## Consequences

### Positive

- **Unified Authentication**: Single Supabase session handles both storage and database access
- **Native RLS Integration**: Bucket policies use same RLS framework as database tables
- **Enhanced Security**: Signed URLs ensure files are never publicly accessible
- **No Additional Credentials**: No separate storage tokens required beyond existing Supabase keys
- **Consistent Platform**: All data (files + metadata) in Supabase ecosystem

### Negative

- **Latency**: Supabase Storage not edge-optimized; uploads route through Supabase infrastructure
- **Signed URL Overhead**: Each file access requires URL signing, adding minimal latency
- **Regional Affinity**: Storage performance tied to Supabase project region

### Neutral

- **Storage Provider Lock-in**: Files stored in Supabase; migration would require re-upload
- **URL Expiration**: Signed URLs expire after 1 hour; long-lived references need refresh logic

## Alternatives Considered

### 1. Vercel Blob (ADR-0058)

Use Vercel Blob for file bytes with Supabase for metadata only.

**Rejected because:**

- Public URLs rely on obscurity rather than true access control
- Requires separate token management (`BLOB_READ_WRITE_TOKEN`)
- No native integration with Supabase RLS
- Additional complexity without proportional benefit

### 2. AWS S3 Direct Integration

Use AWS S3 for storage with presigned URLs.

**Rejected because:**

- Requires additional infrastructure provisioning and credentials management
- No native Supabase integration; more complex deployment configuration
- Higher operational overhead compared to Supabase's managed service

### 3. Continue Proxy Architecture

Maintain the legacy backend proxy for attachments.

**Rejected because:**

- Does not address the fundamental dependency on the retiring backend
- Continues to incur multi-hop latency and operational complexity
- Technical debt accumulates rather than being resolved

## Implementation Notes

### Required Dependencies

- `file-type` (v18+): For magic byte detection and MIME verification
  - Install: `npm install file-type`
  - Validates actual file type matches declared MIME type to prevent spoofing

### Upload Flow (Server-Side)

```typescript
import { secureUuid } from '@/lib/security/random';
import { sanitizeFilename } from '@schemas/attachments';
import { fileTypeFromBuffer } from 'file-type';

// Verify MIME type using magic bytes
const buffer = new Uint8Array(await file.arrayBuffer());
const detected = await fileTypeFromBuffer(buffer);

if (!detected || detected.mime !== file.type) {
  throw new Error('MIME type mismatch');
}

// Upload to Supabase Storage
const storagePath = `chat/${userId}/${secureUuid()}-${sanitizeFilename(file.name)}`;

const { error } = await supabase.storage
  .from('attachments')
  .upload(storagePath, buffer, {
    contentType: detected.mime,
    upsert: false,
  });

// Insert metadata
await supabase.from('file_attachments').insert({
  user_id: userId,
  filename: secureUuid(),           // Storage key (UUID)
  original_filename: file.name,     // User-facing name
  file_size: file.size,
  mime_type: detected.mime,
  file_path: storagePath,           // Full storage path
  bucket_name: 'attachments',
  upload_status: 'completed',
});
```

### Signed URL Generation

```typescript
// Single file
const { data } = await supabase.storage
  .from('attachments')
  .createSignedUrl(path, 3600, { download: true });

// Batch (for listings)
const { data } = await supabase.storage
  .from('attachments')
  .createSignedUrls(paths, 3600, { download: true });
```

**Note on `download: true` option**: Setting `download: true` in the signed URL options forces the browser to download the file as an attachment rather than opening it inline. This prevents XSS attacks where embedded content (e.g., HTML files) could execute in the user's browser context. TTL (time-to-live) is set to 3600 seconds (1 hour).

### Validation Schema (Zod v4)

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
```

### Telemetry

| Operation | Span Name |
|-----------|-----------|
| Upload handler | `chat.attachments.upload` |
| Storage upload | `chat.attachments.storage.upload` |
| Metadata insert | `chat.attachments.metadata.insert` |
| List files | `attachments.files.read` |
| Signed URL generation | `attachments.files.sign` |

## References

- [Supabase Storage Overview](https://supabase.com/docs/guides/storage)
- [Supabase Storage Access Control](https://supabase.com/docs/guides/storage/access-control)
- [Next.js Cache Revalidation](https://nextjs.org/docs/app/getting-started/caching-and-revalidating)
- Supersedes: ADR-0058 (Vercel Blob for Chat Attachments Storage)
- ADR-0040: Consolidate Supabase Edge to Vercel Route Handlers
- SPEC-0017: Attachments Migration Next.js
- SPEC-0037: Attachments V2 Supabase Storage
