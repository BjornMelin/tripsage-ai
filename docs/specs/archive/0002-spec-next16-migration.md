# Spec: Next.js 16 Migration (Proxy, Async APIs, Turbopack)

**Version**: 1.1.0
**Status**: Accepted
**Date**: 2025-10-24

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
- [x] SSR auth page fixes:
  - [x] `src/lib/supabase/server.ts` exists with `createServerSupabase()` wrapper.
  - [x] Verified `app/(auth)/reset-password/page.tsx` correctly uses server-side auth with `createServerSupabase()` and `getCurrentUser()` (no client hooks in server component).
  - [x] Build validation completed - all TypeScript errors resolved, build succeeds.
- [x] Wrap client/dynamic UI usage in `<Suspense>` where necessary to comply with Cache Components prerender rules.
- [x] Removed legacy `dynamic`/`revalidate` segment configs that conflict with `cacheComponents`.
- [x] Docs
  - [x] ADR-0013 captures design.
  - [x] `docs/index.md` lists Next 16 migration notes; users section requires no changes.

## Notes

- Proxy defaults to Node runtime; avoid edge-only assumptions.
- Use matchers to limit proxy scope.
- Async Request APIs are mandatory in v16; consider using `npx next typegen` to adopt `PageProps` helpers for `params/searchParams` typing.
- References:
  - <https://nextjs.org/docs/app/guides/upgrading/version-16>
  - <https://nextjs.org/docs/app/api-reference/file-conventions/proxy>

### 2025-10-23 SSR audit log

- Route handlers reviewed: `app/api/chat/route.ts`, `app/api/chat/attachments/route.ts`, and `app/auth/confirm/route.ts`. The confirm handler is the only Supabase call site and defers to `createServerSupabase()`, which awaits `cookies()` before invoking Supabase APIs to opt out of public caching. Route handlers without Supabase dependencies do not access `cookies()`/`headers()` directly and operate purely on request payloads.
- `app/api/chat/attachments/route.ts` now revalidates the `attachments` cache tag for both single and batch payloads right before returning, using `revalidateTag('attachments', 'max')` to mark cache entries stale without blocking.
- Chat: Next.js chat routes are canonical with AI SDK v6: `/api/chat/stream` (SSE) and `/api/chat` (JSON). The UI calls these routes directly; FastAPI chat endpoints are removed.
- The attachments endpoint uses Upstash Redis caching (not Next.js Cache Components) since it accesses `cookies()` via `withApiGuards({ auth: true })`.
  Routes accessing `cookies()` or `headers()` cannot use `"use cache"` directives per Next.js Cache Components restrictions.
  See [Spec: BYOK Routes and Security (Next.js + Supabase Vault)](../specs/0011-spec-byok-routes-and-security.md).

## Additional Optimizations Completed (2025-11-25)

- [x] Added Turbopack file system cache configuration (`turbopackFileSystemCacheForDev`)
- [x] Verified `optimizePackageImports` remains in experimental (correct for Next.js 16.0.3)
- [x] Fixed TypeScript errors:
  - Exported `TripSuggestion` type from `use-trips.ts`
  - Fixed `isEmailVerified` usage in account settings (removed invalid profile reference)
  - Fixed type errors in `optimistic-trip-updates.tsx` (changed `Trip` to `UiTrip`)
  - Added `currency` property to trip export test mock
- [x] Fixed security dashboard server component import issue (using dynamic import with Suspense)
- [x] Fixed admin configuration page static generation issue (removed `"use cache: private"` directive - route accesses `cookies()` via `createServerSupabase()` and must be dynamic per Next.js Cache Components restrictions)
- [x] All route handlers verified to use async `params` (already compliant)

## Changelog

- 1.2.0 (2025-11-25)
  - Completed middleware -> proxy migration
  - Fixed all TypeScript errors
  - Added Turbopack file system cache configuration
  - Verified all route handlers use async params
  - Fixed server component import issues
  - Build validation completed successfully
- 1.1.0 (2025-10-24)
  - Clarified `revalidateTag('attachments', 'max')` usage and removed ambiguous phrasing.
  - Added versioned metadata (semver) and changelog section.
- 1.0.0 (2025-10-23)
  - Initial specification for v16 migration (proxy, async APIs, turbopack).
