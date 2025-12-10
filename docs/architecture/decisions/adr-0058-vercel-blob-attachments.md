# ADR-0058: Vercel Blob for Chat Attachments Storage

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-12-10
**Category**: Architecture/Storage
**Domain**: Attachments, File Storage
**Related ADRs**: ADR-0040
**Related Specs**: SPEC-0017, SPEC-0036

## Context

The TripSage application currently handles chat attachments through a proxy architecture where Next.js Route Handlers forward requests to a legacy FastAPI backend (`getBackendApiUrl()`). This architecture was implemented as an interim solution during the migration to a frontend-only Next.js deployment on Vercel.

### Current Architecture

```text
Client → POST /api/chat/attachments → Next.js Route Handler → FastAPI Backend → Storage
Client → GET /api/attachments/files → Next.js Route Handler → FastAPI Backend → Database
```

### Drawbacks of Current Architecture

1. **Hidden Runtime Dependency**: The application depends on a legacy backend service that is scheduled for retirement. This creates an implicit dependency that is not visible in the deployment configuration.

2. **Multi-Hop Network Path**: Every attachment operation requires an extra network hop through the proxy layer, adding latency and points of failure.

3. **Fragmented Observability**: Errors and performance issues span two systems, making debugging complex. Telemetry is split between Next.js and FastAPI services.

4. **Operational Complexity**: Two separate deployment pipelines, environments, and monitoring systems must be maintained.

5. **Inconsistent Error Handling**: Error responses from the backend must be transformed before returning to the client, leading to potential information loss.

## Decision

We will migrate chat attachments storage to use **Vercel Blob** for file bytes and **Supabase** for metadata with RLS-enforced ownership. This approach:

1. **Uses Vercel Blob** (`@vercel/blob`) for storing attachment file bytes:
   - Server-side uploads via `put()` for small/medium files (up to 10MB per file)
   - Public access mode with deterministic paths for efficient CDN caching
   - Optional random suffix to prevent naming collisions

2. **Uses Supabase** for attachment metadata:
   - Existing `file_attachments` table stores ownership, file metadata, and Blob URLs
   - RLS policies enforce user-level access control
   - Enables filtering by `trip_id`, `chat_message_id`, `user_id`

3. **Chat attachments first**: Begin with chat attachments; extend to trip images and avatars in subsequent phases.

### Object Key Scheme

Attachment paths follow a deterministic scheme:

```text
chat/{user_id}/{uuid}-{sanitized_filename}
trip/{trip_id}/{uuid}-{sanitized_filename}
user/{user_id}/avatar/{uuid}-{sanitized_filename}
```

- `{user_id}` and `{trip_id}` are UUIDs
- `{uuid}` is a secure random UUID for uniqueness
- `{sanitized_filename}` preserves original name for human readability

### Implementation Approach

1. **Server-side uploads**: Use `put()` from `@vercel/blob` with streaming body
2. **Metadata persistence**: Insert into `file_attachments` after successful Blob upload
3. **Validation**: Zod v4 schemas enforce size limits, MIME types, and file counts
4. **Cache invalidation**: Use `revalidateTag('attachments')` and Upstash `bumpTag()` for listing cache

### Future Enhancement (TODO)

Client-side uploads via `handleUpload()` + `upload()` for large files can be implemented when needed. See: [Vercel Blob client upload docs](https://vercel.com/docs/vercel-blob/client-upload)

## Consequences

### Positive

- **Simplified Architecture**: Single deployment surface on Vercel; no legacy backend dependency for attachments
- **Improved Performance**: Direct uploads to Vercel's edge-optimized Blob storage; global CDN distribution
- **Unified Observability**: All telemetry in one platform (Vercel + OpenTelemetry)
- **Scalability**: Vercel Blob scales automatically; no capacity planning required
- **Cost Efficiency**: Pay-per-use storage model; no idle infrastructure costs

### Negative

- **Environment Setup**: Each environment (dev, staging, prod) requires its own Blob store token
- **Migration Effort**: Existing historical attachments in the legacy system require a migration path (not in scope for v1)
- **Feature Parity**: Some legacy features (e.g., virus scanning integration) may need reimplementation

### Neutral

- **Storage Provider Lock-in**: Vercel Blob is Vercel-specific; future migration would require URL rewrites
- **Public URLs**: Blob URLs are publicly accessible (with random suffixes for obscurity); sensitive files may need signed URL layer

## Alternatives Considered

### 1. Supabase Storage Only

Use Supabase Storage for both file bytes and metadata.

**Rejected because:**

- Additional latency for uploads (Supabase Storage is not edge-optimized like Vercel Blob)
- Different authentication model (Supabase JWT vs Vercel's native integration)
- We already have Vercel as primary deployment platform; prefer native integrations

### 2. Continue Proxy Architecture with Improvements

Maintain the proxy pattern but improve error handling and observability.

**Rejected because:**

- Does not address the fundamental dependency on the retiring backend
- Continues to incur multi-hop latency and operational complexity
- Technical debt accumulates rather than being resolved

### 3. AWS S3 Direct Integration

Use AWS S3 for storage with signed URLs.

**Rejected because:**

- Requires additional infrastructure provisioning and credentials management
- No native Vercel integration; more complex deployment configuration
- Higher operational overhead compared to Vercel Blob's managed service

## Implementation Notes

### Environment Variables

```bash
# Required: Vercel Blob read/write token
BLOB_READ_WRITE_TOKEN=vercel_blob_rw_xxx

# Optional: Custom public base URL (for branded domains)
BLOB_PUBLIC_BASE_URL=https://attachments.tripsage.ai
```

### Upload Flow (Server-Side)

```typescript
import { put } from '@vercel/blob';
import { secureUuid } from '@/lib/security/random';

const blob = await put(
  `chat/${userId}/${secureUuid()}-${sanitizedFilename}`,
  file.stream(),
  {
    access: 'public',
    addRandomSuffix: false, // We add our own UUID
    contentType: file.type,
  }
);

// Insert metadata into Supabase
// Note: filename = internal storage identifier (UUID)
//       original_filename = user-facing display name
//       file_path = full object path in blob storage
await supabase.from('file_attachments').insert({
  user_id: userId,
  filename: secureUuid(),        // Internal UUID identifier
  original_filename: file.name,   // Original user-provided filename
  file_size: file.size,
  mime_type: file.type,
  file_path: blob.pathname,       // Full storage path (e.g., "chat/user-id/uuid-file.jpg")
  bucket_name: 'vercel_blob',
  upload_status: 'completed',
});
```

### Validation Schema (Zod v4)

```typescript
import { z } from 'zod';

export const uploadAttachmentSchema = z.object({
  files: z.array(z.instanceof(File))
    .min(1, { error: 'At least one file is required' })
    .max(5, { error: 'Maximum 5 files per request' }),
});

export const ALLOWED_MIME_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
] as const;
```

## References

- [Vercel Blob Overview](https://vercel.com/docs/storage/vercel-blob)
- [Vercel Blob Server Upload](https://vercel.com/docs/storage/vercel-blob/server-upload)
- [Vercel Blob Client Upload](https://vercel.com/docs/vercel-blob/client-upload)
- [Next.js Cache Revalidation](https://nextjs.org/docs/app/getting-started/caching-and-revalidating)
- ADR-0040: Consolidate Supabase Edge to Vercel Route Handlers
- SPEC-0017: Attachments Migration Next.js
- SPEC-0036: Attachments V2 Vercel Blob
