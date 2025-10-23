# ADR-0018: Centralize Supabase typed helpers for CRUD

**Date**: 2025-10-23

## Status

Accepted

## Context

We migrated to `@supabase/ssr` and generated `database.types.ts` for strict typing. In practice, direct usage of the PostgREST generics (`from().insert<...>()`) can be brittle across versions and often leads to scattered `(supabase as any)` casts to satisfy method chaining (`.select().single()`). This weakens type guarantees and spreads runtime casts across the codebase.

## Decision

We introduced `src/lib/supabase/typed-helpers.ts` that:

- Enforces `InsertTables<T>`/`UpdateTables<T>` at compile time, keeping call sites strongly typed.
- Centralizes the single runtime `any` escape hatch while returning `{ data, error }`—the minimum needed by hooks.
- Provides `insertSingle()` and `updateSingle()` helpers used in `use-supabase-chat.ts`, `use-supabase-storage.ts`, and `use-trips-supabase.ts`.

Follow-ups:

- Add a `selectHeadCount()` helper to standardize count queries used with `{ head: true }` patterns.
- Consider an overload for multi-row inserts (without `.single()`) or expose an `insertMany()` helper to avoid accidental `.single()` with arrays.

## Consequences

### Positive

- Removes scattered `(supabase as any)` while preserving strict shapes at the edges.
- Easier future library upgrades—runtime PostgREST nuances are isolated.
- Clearer testing seams and opportunity to add compile-time (tsd) smoke tests.

### Negative

- Helpers currently drop PostgREST status/warnings—callers only receive `{ data, error }`. If needed, we will extend return types.
- The `where` callback in `updateSingle()` is currently typed as `any` to preserve fluent filters; we will refine if common patterns emerge.

### Neutral

- This is a thin layer, not an abstraction of queries; developers still build filters and selects per call site.

## Alternatives Considered

### Direct PostgREST generics everywhere

Rejected. Causes repeated casts, mixed `.single()` semantics, and version-specific type gymnastics. Centralization reduces churn.

### Custom repository layer per domain (Trips/Chat/Files)

Deferred. May be valuable later, but the helper approach yields 80% of the benefit with minimal ceremony.

## References

- Supabase SSR for Next.js (server-side client & cookies). See docs.
- Generated types pattern (`Database`, `Tables`, `InsertTables`, `UpdateTables`).
