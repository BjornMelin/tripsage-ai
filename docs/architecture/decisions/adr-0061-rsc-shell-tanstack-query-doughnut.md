# ADR-0061: RSC shell + TanStack Query “doughnut” architecture

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2026-01-05  
**Category**: frontend + fullstack  
**Domain**: Next.js App Router, data fetching, caching

## Context

TripSage is an AI-heavy application where:

- The initial render must be fast, streamed, and SEO-friendly where relevant.
- The UI contains long-lived, highly interactive “sessions” (chat, trip planning iterations, tool calls).
- Server Actions are ideal for trusted mutations but are not a full client state solution.
- Pure server-driven state causes slow UX for interactive flows (no optimistic updates by default).

## Decision

Adopt a “doughnut” architecture:

- **Outer shell (Server Components)**:
  - Fetch initial data directly on the server (RSC).
  - Prefetch and dehydrate TanStack Query state where the page requires interactive follow-up reads.
  - Use function-level caching via `use cache` for safe, pure read functions.
- **Inner filling (Client Components)**:
  - Use TanStack Query as the authoritative client session cache for reads, optimistic updates, retries, polling, and dedupe.
  - Mutations call Server Actions (transport layer) and update/invalidate query cache.

## Consequences

### Positive

- Fast initial render via RSC, streaming, and server-side data fetching.
- Best-in-class interactive UX using TanStack Query (optimistic updates, refetch control).
- Reduced client waterfalls and duplicated requests via query cache dedupe.

### Negative / tradeoffs

- Requires consistent query key design and cache invalidation discipline.
- Introduces one more dependency and learning surface (TanStack Query), but it is stable and widely used.

## Implementation rules

1) Server reads live in `src/server/queries/*` and must be:

- Pure, side-effect free, and safe to cache.
- Validated output (Zod) at the boundary.

1) Client reads use `useQuery` with:

- Stable `queryKey` from `src/lib/keys.ts`
- `queryFn` calling a typed Route Handler only when a read cannot be done server-side (rare).

1) Avoid “internal REST” for mutations:

- Mutations must be Server Actions, except for webhooks and streaming endpoints.

## References (official)

```text
TanStack Query Advanced SSR (Next.js App Router): https://tanstack.com/query/v5/docs/react/guides/advanced-ssr
TanStack Query SSR Hydration guide: https://tanstack.com/query/v5/docs/react/guides/ssr
Next.js App Router docs: https://nextjs.org/docs/app
Next.js `use cache` directive: https://nextjs.org/docs/app/api-reference/directives/use-cache
```
