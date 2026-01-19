# SPEC-0100: Application architecture (Next.js RSC + TanStack Query)

**Version**: 1.1.0  
**Status**: Final  
**Date**: 2026-01-19

## Goals

- Fast initial render via RSC with minimal client bundle.
- Interactive “session” UX via TanStack Query, including optimistic updates.
- Strict validation at all boundaries via Zod v4.
- Clean separation between:
  - server reads (cached)
  - server writes (actions)
  - streaming/webhook APIs (route handlers)

## Non-goals

- Building a public REST API surface for all internal operations.
- Supporting legacy/deprecated Next.js APIs or patterns.
- Supporting Next.js static export mode (`output: "export"`). TripSage relies on cookies/authenticated SSR, Route Handlers beyond `GET`, and server-only integrations that require a server runtime.

## Architecture overview

### Outer shell (RSC)

- Each page fetches the initial data server-side:
  - authenticated user
  - trip summary, chat session metadata, etc.
- Pages prefetch TanStack Query where interactive follow-up reads occur.

### Inner filling (Client)

- TanStack Query drives interactive reads and mutations.
- Server Actions are used as mutation functions.

### Directory ownership

- `src/app/*`: routing + layouts + server entrypoints
- `src/features/*`: feature-specific code
- `src/server/*`: server-only code
- `src/components/ui`: shadcn/ui

## Data flow contract

1) Ingress (UI → Action)

   - Form submits to server action.
   - Action validates with Zod, performs DB mutation, returns typed result.

2) Read (RSC)

   - RSC calls `src/server/queries/*` which use `use cache` when safe (see [ADR-0064](../../architecture/decisions/adr-0064-caching-use-cache-and-consistency-rules.md) for cache criteria and invalidation strategy).

3) Read (Client)

   - `useQuery` uses server-prefetched dehydrated state or fetches via a small Route Handler only when needed (cache misses, refocus, manual retry; see [ADR-0064](../../architecture/decisions/adr-0064-caching-use-cache-and-consistency-rules.md)).

## TanStack Query foundation (canonical paths)

### Query keys

- Canonical factory: `src/lib/keys.ts`
- Conventions:
  - Keys are stable arrays (no ad-hoc strings).
  - Keys are grouped by feature (e.g. `keys.trips.*`, `keys.chat.*`).
  - **Private data is always scoped by `userId`** (e.g. `keys.trips.list(userId)`, `keys.trips.detail(userId, tripId)`).

### Query client + SSR hydration

- Query client configuration (server + client): `src/lib/query/query-client.ts`
- Server prefetch + dehydration helper: `src/lib/query/prefetch.ts`
- Hydration wrapper: `src/lib/query/hydration-boundary.tsx`

### Provider integration (authenticated routes)

- App providers: `src/app/(app)/providers.tsx`
- Provider wiring layout: `src/app/(app)/layout.tsx`

## Performance requirements

- Avoid client waterfalls (RSC prefetch + hydration boundary).
- Prefer server-only components by default.
- No manual `useMemo` or `useCallback` (React compiler).

## References

```text
Next.js `use cache` directive: https://nextjs.org/docs/app/api-reference/directives/use-cache
Next.js caching and `use cache`: https://nextjs.org/docs/app/getting-started/caching
Next.js static exports (limitations): https://nextjs.org/docs/app/guides/static-exports
TanStack Query Advanced SSR: https://tanstack.com/query/v5/docs/react/guides/advanced-ssr
Zod v4 Documentation: https://zod.dev/
```
