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
- [ ] Audit all server components/route handlers:
  - [ ] For each usage of `cookies()`, `headers()`, ensure async patterns.
  - [ ] For `params`/`searchParams`, use async props or Next typegen helpers where applicable.
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
