# Spec: Next.js 16 Migration (Proxy, Async APIs, Turbopack)

Owner: Frontend Platform
Status: In progress
Last updated: 2025-10-23

## Objective

Upgrade the app to Next.js 16 by migrating middleware -> proxy, enforcing async Request APIs, and finalizing turbopack config. Ensure all SSR pages comply and builds/prerenders are clean.

## Scope

- Replace middleware.ts with proxy.ts.
- Ensure all usage of `cookies`, `headers`, `draftMode`, and route `params/searchParams` are async.
- Fix SSR auth on sensitive routes (e.g., reset-password page) to avoid client hooks in server.

## Implementation Checklist

- [x] Replace `src/middleware.ts` with `src/proxy.ts`; export `proxy()`.
- [x] Keep existing `matcher` negative lookahead for static/image files.
- [x] Move `experimental.turbopack` to top-level `turbopack` in `next.config.ts`.
- [x] Audit all server components/route handlers:
  - [x] Verified `createServerSupabase()` awaits `cookies()` before auth calls in `app/auth/confirm/route.ts`.
  - [x] Confirmed route handlers (`app/api/chat/route.ts`, `app/api/chat/attachments/route.ts`) avoid synchronous Request APIs and operate on payloads only.
- [ ] SSR auth page fixes:
  - [x] `src/lib/supabase/server.ts` exists with `createServerSupabase()` wrapper.
  - [ ] Update `app/(auth)/reset-password/page.tsx` to server-read auth with the server client (no `useAuth` hook in server). If client interactivity is required, split into server + client child.
  - [ ] Validate build no longer fails at prerender.
- [x] Wrap client/dynamic UI usage in `<Suspense>` where necessary to comply with Cache Components prerender rules.
- [x] Removed legacy `dynamic`/`revalidate` segment configs that conflict with `cacheComponents`.
- [ ] Docs
  - [x] ADR-0013 captures design.
  - [ ] Update `docs/index.md` and `docs/users` for downstream effects.

## Notes

- Proxy defaults to Node runtime; avoid edge-only assumptions.
- Use matchers to limit proxy scope.
- Async Request APIs are mandatory in v16; consider using `npx next typegen` to adopt `PageProps` helpers for `params/searchParams` typing.
- References:
  - <https://nextjs.org/docs/app/guides/upgrading/version-16>
  - <https://nextjs.org/docs/app/api-reference/file-conventions/proxy>

### 2025-10-23 SSR audit log

- Route handlers reviewed: `app/api/chat/route.ts`, `app/api/chat/attachments/route.ts`, and `app/auth/confirm/route.ts`. The confirm handler is the only Supabase call site and defers to `createServerSupabase()`, which awaits `cookies()` before invoking Supabase APIs to opt out of public caching. Route handlers without Supabase dependencies do not access `cookies()`/`headers()` directly and operate purely on request payloads.
- `app/api/chat/attachments/route.ts` now revalidates the `attachments` cache tag for both single and batch payloads right before returning, using the `profile="max"` option to mark cache entries stale without blocking.citeturn0view0
- The attachments endpoint remains annotated with `"use cache: private"` so uploads stay user-scoped while allowing follow-up fetches to reuse cached metadata where appropriate.
