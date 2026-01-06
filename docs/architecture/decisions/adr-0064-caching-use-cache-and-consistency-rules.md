# ADR-0064: Caching with `use cache` and consistency rules

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2026-01-05  
**Category**: fullstack  
**Domain**: caching, performance, correctness

## Context

TripSage has:

- expensive reads (RAG, search, trip aggregation)
- repeated reads across server components
- interactive client sessions

Caching must improve performance without creating correctness bugs (cross-user leakage, stale writes).

## Decision

- Use Next.js function-level caching via `use cache` for server read functions that are:
  - deterministic for the given input parameters
  - scoped correctly (include userId or tenantId if required)
  - safe to share (no secrets in return values)
- Do not use cache for:
  - reads that depend on auth cookies implicitly but do not take a user id parameter
  - reads returning highly volatile state where staleness breaks UX (use TanStack Query client cache)

Consistency rules:

- Every mutation Server Action must explicitly invalidate affected client query keys.
- For server reads used in RSC rendering, prefer “read-your-writes” by redirecting after mutation to a route that refetches fresh state.

## Consequences

- Performance wins are explicit and controlled.
- Reduced risk of cross-user caching bugs.
- Requires discipline in query key design and mutation invalidation.

## References

```text
Next.js `use cache` directive: https://nextjs.org/docs/app/api-reference/directives/use-cache
Next.js caching overview: https://nextjs.org/docs/app/getting-started/caching
TanStack Query caching concepts: https://tanstack.com/query/v5/docs/react/overview
```
