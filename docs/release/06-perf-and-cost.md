# TripSage AI — Performance & Cost (v1.0.0)

## Principles

- Free-tier friendly defaults for Vercel + Supabase + Upstash.
- Avoid client waterfalls; Server Components by default.
- Cache safely (never cache user-specific/cookie-dependent data publicly).

## Performance Targets (initial)

- Landing page interactive without client-side boot storms.
- No obvious long tasks from excessive client components.
- Avoid unnecessary rerenders; prefer server data fetching.

## Cost Controls

- Rate limit AI generation and expensive API calls.
- Avoid logging large payloads.
- Make LLM provider selection explicit and safe (no accidental paid models).

## Known Risk Areas

- AI streaming endpoints (`/api/ai/stream`, `/api/chat`) can generate cost spikes if not rate limited and fail-closed under degraded infra.
- Travel API endpoints (flights/accommodations/activities) can exhaust third-party quotas.
- File uploads (`/api/chat/attachments` signed uploads to Supabase Storage) can increase storage/egress costs; enforce size limits and auth checks.

## Action Items

Tracked via `docs/tasks/INDEX.md`.
