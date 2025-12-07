# SPEC-0017: Attachments & File Uploads Migration (Next.js)

**Version**: 1.0.0  
**Status**: Partial (Proxy Implementation)  
**Date**: 2025-11-04

## Overview

- Goal: Replace FastAPI attachments endpoints with Next.js Route Handlers using Supabase Storage, signed URLs, MIME/size validation, and stricter rate limits.

**Current Status:** Upload endpoint (`POST /api/chat/attachments`) proxies to backend FastAPI. Listing endpoint (`GET /api/attachments/files`) also proxies to backend. Direct Supabase Storage integration is pending.

## Routes (Current Implementation)

- `POST /api/chat/attachments` — Proxies to backend FastAPI `/api/attachments/upload` or `/api/attachments/upload/batch`. Validates multipart form data, enforces 10MB per-file cap, max 5 files per request, and rejects requests advertising total payload >50MB via `Content-Length`. Auth is bound to the current Supabase session cookie (`sb-access-token`); caller `Authorization` headers are ignored and never forwarded. Uses `withApiGuards` for auth and rate limiting (`chat:attachments`). Revalidates `attachments` cache tag on success.
- `GET /api/attachments/files` — Proxies to backend FastAPI `/api/attachments/files` with pagination. Uses `withApiGuards` with rate limiting (`attachments:files`). Participates in cache tag invalidation via `next: { tags: ['attachments'] }`.

## Routes (Target Implementation - Not Yet Migrated)

- `POST /api/attachments/upload` — Direct Supabase Storage upload (images/pdf only), size cap 10MB.
- `GET /api/attachments` — Direct Supabase query with pagination; cache tags.
- `GET /api/attachments/:id/url` — Short-lived signed URL (viewer-specific) from Supabase Storage.

## Design

- Storage: Supabase Storage bucket `attachments` with RLS via signed URLs.
- Validation: MIME sniff + extension check; reject spoofed types.
- Rate limits: upload 10/min/user, list 60/min/user.
- Observability: spans `attachments.upload`, `attachments.sign`.

### Storage buckets & paths

- Buckets in scope: `attachments` (chat), `trip-images` (itinerary media), `avatars` (profile images).
- Path conventions:
  - Trip-scoped: `trip/{trip_id}/{uuid-filename}`.
  - User-scoped: `user/{user_id}/{uuid-filename}`.
- Relational link: `public.file_attachments.file_path` stores the full object name; unique index on `file_path`.

### RLS & ownership

- Table ownership: `file_attachments` currently stores `user_id` (no `owner_id` column). Table-level RLS enforces `auth.uid() = user_id`.
- Storage bucket RLS handles trip collaboration: path-based rules (`trip/{trip_id}/...`) call `user_has_trip_access()` to allow trip owners/collaborators; user-scoped paths rely on `auth.uid()` matches.
- Signed URL generation and deletion must validate against `file_attachments` and bucket RLS; avoid assuming a separate `owner_id` field.

### Cleanup & audits

- Attachments rely on the relational link for lifecycle; when a message/trip is deleted, delete the corresponding `file_attachments` row and storage object.
- Use the storage owner audit runbook (`docs/operations/runbooks/storage-owner-audit.md`) to find path/owner mismatches or orphaned objects; run after RLS/schema changes.

## Security

- Never store raw URLs; return signed URLs only.
- Verify ownership before signing.
- Sanitize filenames; generate UUID object names.

## Testing

- Multipart parsing (boundary errors, empty parts).
- MIME spoofing detection.
- Oversize rejection with 413; correct `Retry-After` for RL.
- Signed URL TTL and ownership validation.

## Acceptance Criteria

- All routes SSR-authenticated; no public endpoints.
- Edge-safe for list/sign; Node runtime allowed for multipart if needed.
- Remove FastAPI attachments router and fixtures.

## References

- Supabase Storage: <https://supabase.com/docs/guides/storage>
- Next.js Route Handlers: <https://nextjs.org/docs/app/building-your-application/routing/route-handlers>
