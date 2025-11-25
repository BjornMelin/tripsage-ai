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
  - Uses `withApiGuards({ auth: true })` which accesses `cookies()` for authentication.
  - Implements per-user caching via Upstash Redis (2-minute TTL) to keep attachment listings near real time for collaborative scenarios while still shaving backend reads; Next.js Cache Components cannot be used when accessing `cookies()` or `headers()`.
    - Rationale: 2 minutes balances freshness for collaborators (upload → list) against Supabase load; longer TTLs (5–15 minutes) further reduce DB/Redis traffic but increase staleness risk.
    - Configurability: TTL must be configurable per deployment (recommended default: 120s) via an environment/config key (e.g., `ATTACHMENTS_CACHE_TTL_SECONDS`); teams should tune based on collaboration intensity and load targets.
    See [Spec: BYOK Routes and Security (Next.js + Supabase Vault)](../specs/0011-spec-byok-routes-and-security.md).
  - Returns JSON (200) or propagates backend error status with a concise error body.
  - Route is dynamic by default (no `"use cache"` directive) due to `cookies()` access.

## Invalidation

- Upload handler (`POST /api/chat/attachments`) calls `revalidateTag('attachments', 'max')` on success.
- On subsequent visit to pages/data using the `attachments` tag, cached data is revalidated in the background.

## Testing

- Unit test ensures Authorization forwarding and presence of `next.tags = ['attachments']` in fetch options.

## Changelog

- 1.0.0 (2025-10-24)
  - Initial specification and implementation.
