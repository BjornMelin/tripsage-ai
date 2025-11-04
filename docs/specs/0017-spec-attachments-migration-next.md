# Spec: Attachments & File Uploads Migration (Next.js)

Overview

- Goal: Replace FastAPI attachments endpoints with Next.js Route Handlers using Supabase Storage, signed URLs, MIME/size validation, and stricter rate limits.

Routes (suggested)

- `POST /api/attachments/upload` — authenticated multipart upload (images/pdf only), size cap 10MB.
- `GET /api/attachments` — list by owner with pagination; cache tags.
- `GET /api/attachments/:id/url` — short-lived signed URL (viewer-specific).

Design

- Storage: Supabase Storage bucket `attachments` with RLS via signed URLs.
- Validation: MIME sniff + extension check; reject spoofed types.
- Rate limits: upload 10/min/user, list 60/min/user.
- Observability: spans `attachments.upload`, `attachments.sign`.

Security

- Never store raw URLs; return signed URLs only.
- Verify ownership before signing.
- Sanitize filenames; generate UUID object names.

Testing

- Multipart parsing (boundary errors, empty parts).
- MIME spoofing detection.
- Oversize rejection with 413; correct `Retry-After` for RL.
- Signed URL TTL and ownership validation.

Acceptance Criteria

- All routes SSR-authenticated; no public endpoints.
- Edge-safe for list/sign; Node runtime allowed for multipart if needed.
- Remove FastAPI attachments router and fixtures.

References

- Supabase Storage: <https://supabase.com/docs/guides/storage>
- Next.js Route Handlers: <https://nextjs.org/docs/app/building-your-application/routing/route-handlers>
