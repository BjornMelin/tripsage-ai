# ADR-0014: Migrate Supabase auth to @supabase/ssr; deprecate auth-helpers-react

**Date**: 2025-10-23

## Status

Accepted

## Context

`@supabase/auth-helpers-react` is deprecated; Supabase recommends `@supabase/ssr` for both server and browser clients with cookie-based session refresh.

## Decision

- Consolidate browser client via `createBrowserClient<Database>()` and expose as a singleton.
- Use `createServerClient()` within proxy and server components/actions for SSR-safe auth (`auth.getUser()`).
- Remove `SessionContextProvider` and rely on our `AuthProvider` that consumes the typed client.

## Consequences

### Positive

- Fewer dependencies; consistent SSR/browser semantics; explicit cookie refresh path.

### Negative

- Must verify no remaining helper hooks are referenced.

### Neutral

- Auth flow remains entirely within Supabase; patterns shift to a single typed client and SSR cookie handling rather than helper-specific React providers.

## Alternatives Considered

### Alternative 1 — Keep `@supabase/auth-helpers-react`

Rejected: the helpers are deprecated and diverge from the recommended SSR approach. Staying would increase maintenance risk.

### Alternative 2 — Implement custom cookie/session handling

Rejected: `@supabase/ssr` already provides first-class utilities; bespoke handling would add risk and complexity with little benefit.

## References

- Supabase SSR docs; Next.js SSR guidance for auth and cookies.
  - <https://supabase.com/docs/guides/auth/server-side/nextjs>
  - <https://supabase.com/docs/guides/auth/server-side#supabasessr>
