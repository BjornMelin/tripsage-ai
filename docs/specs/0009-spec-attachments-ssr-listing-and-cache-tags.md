# Spec: Attachments SSR Listing with Cache Tags

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-10-24

## Objective

Serve a user-scoped attachments listing via a Next.js Route Handler that participates in tag-based cache invalidation triggered by uploads.

## Route

- `GET /api/attachments/files`
  - Forwards `Authorization` header when present.
  - Preserves `limit`/`offset` query parameters.
  - Performs a server fetch to `${BACKEND_API_URL}/api/attachments/files` with `next: { tags: ['attachments'] }`.
  - Returns JSON (200) or propagates backend error status with a concise error body.
  - Annotated with `"use cache: private"` to prevent public cache pollution.

## Invalidation

- Upload handler (`POST /api/chat/attachments`) calls `revalidateTag('attachments', 'max')` on success.
- On subsequent visit to pages/data using the `attachments` tag, cached data is revalidated in the background.

## Testing

- Unit test ensures Authorization forwarding and presence of `next.tags = ['attachments']` in fetch options.

## Changelog

- 1.0.0 (2025-10-24)
  - Initial specification and implementation.
