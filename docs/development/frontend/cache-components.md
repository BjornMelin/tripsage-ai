---
title: Cache Components (Next.js 16)
---

## Cache Components (Next.js 16)

This repo enables **Cache Components** via `cacheComponents: true` in `next.config.ts`.

Use Cache Components to get **Partial Prerendering (PPR)**: a mostly-static shell that can stream in dynamic islands (e.g., auth/session-dependent UI) without forcing the entire route to render dynamically.

## When to use `'use cache'`

Use `'use cache'` for **server-side async work** that:

- Is safe to reuse across requests (not user-specific unless keyed by stable input args)
- Does not require request-time data like `cookies()` / `headers()`
- Benefits from amortization (DB reads, remote API calls, expensive transforms)

Examples:

- Marketing/legal routes that should be CDN-fast even when `proxy.ts` is present
- Static configuration reads that change rarely

## When NOT to use `'use cache'`

Avoid `'use cache'` for:

- Authenticated pages/components that read `cookies()` / `headers()` or depend on session
- UI that must reflect per-request state (e.g., personalization, live notifications)

If you must cache while using runtime APIs, use `'use cache: private'` **only** when required.

## Recommended defaults

- Prefer component/function-level caching over file-level unless the whole module is safe.
- Always set an explicit lifetime with `cacheLife(...)` when the default profile is not appropriate.
- When cached data has a clear invalidation signal, tag it with `cacheTag(...)` and invalidate via `revalidateTag(...)`.
  - Prefer `revalidateTag(tag, { expire: 0 })` for immediate expiration semantics (common for admin/config updates and webhook-driven invalidation).
  - Avoid `updateTag(...)` in Route Handlers; it is intended for Server Actions / same-request consumers.

## Request-scoped memoization (React.cache)

Cache Components (`'use cache'`) are for **cross-request** caching. Separately, Next.js recommends using `React.cache` for **request-scoped** deduplication to avoid repeated work inside a single render (nested layouts/pages, repeated helpers).

Repo examples:

- `createServerSupabase()` in `src/lib/supabase/server.ts` memoizes by cookie store, so repeated calls within a request reuse the same Supabase SSR client.
- `getOptionalUser()` in `src/lib/auth/server.ts` is memoized to avoid redundant `supabase.auth.getUser()` calls across nested layouts/pages.

## Shared server reads with tags

For server-only reads that are safe to cache across requests (no `cookies()` / `headers()` / `searchParams`), prefer:

- `'use cache'` (function/component scope)
- `cacheTag(...)` for invalidation
- `cacheLife(...)` for explicit lifetimes

Repo example:

- `resolveAgentConfig()` in `src/lib/agents/config-resolver.ts` caches agent configuration with:
  - tags: `configuration`, `configuration:{agentType}`, `configuration:{agentType}:{scope}`
  - default lifetime via `cacheLife("agentConfiguration")` (custom profile configured in `next.config.ts`)
  - invalidation in Route Handlers via `revalidateTag(..., { expire: 0 })` after config updates/rollbacks.
  - table-driven invalidation via `src/app/api/hooks/cache/route.ts` using `src/lib/cache/registry.ts` (includes `agent_config*` tables).

> Note: This repo includes a small typing shim in `@types/next-cache-components.d.ts` to ensure `cacheLife("<custom-profile>")` remains type-safe under bundler resolution.

## Repo examples

- Cached marketing routes with explicit lifetime:
  - `src/app/(marketing)/contact/page.tsx`
  - `src/app/(marketing)/privacy/page.tsx`
  - `src/app/(marketing)/terms/page.tsx`

## References

- Next.js: “Cache Components” and “use cache” directives (see `.next-docs/`).
