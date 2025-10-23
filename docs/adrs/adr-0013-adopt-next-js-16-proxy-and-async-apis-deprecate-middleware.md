# ADR-0013: Adopt Next.js 16 proxy and async APIs; deprecate middleware

**Date**: 2025-10-23

## Status

Accepted

## Context

Next.js 16 deprecates the `middleware` file convention in favor of `proxy`. It also enforces async Request APIs (`cookies`, `headers`, `draftMode`, async `params`/`searchParams`). Our app used `middleware.ts` and relied on earlier compat.

## Decision

- Replace `src/middleware.ts` with `src/proxy.ts` exporting a `proxy(request: NextRequest)` function.
- Keep the route `matcher` equivalent.
- Use Node runtime assumptions for proxy and move Turbopack config to top-level `turbopack` in `next.config.ts`.

## Consequences

### Positive

- Aligns with Next 16 architecture; clearer network boundary and build/runtime consistency.
- Reduces future deprecation risk; enables improved navigation/caching.

### Negative

- Requires auditing SSR code using cookies/headers to ensure async usage semantics.

### Neutral

- Clarifies separation between network-time logic (proxy) and render-time logic (routes). Some logic placement may shift but behavior remains equivalent when implemented correctly.

## Alternatives Considered

### Alternative 1 — Keep `middleware.ts`

Rejected. The convention is deprecated in v16; continued usage risks future breakages and blocks adoption of new routing/runtime features.

### Alternative 2 — Defer upgrade and remain on Next 15

Rejected. Delays access to v16 improvements (Turbopack default, routing/navigation, cache components path), and allows deprecations to accumulate, increasing future migration cost.

## References

- Next.js 16 upgrade guide and proxy file-convention documentation.
  - <https://nextjs.org/docs/app/guides/upgrading/version-16>
  - <https://nextjs.org/docs/app/api-reference/file-conventions/proxy>
