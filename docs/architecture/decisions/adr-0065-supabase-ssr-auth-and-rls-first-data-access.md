# ADR-0065: Supabase SSR auth and RLS-first data access

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2026-01-05  
**Category**: backend + security  
**Domain**: auth, database, multi-tenancy

## Context

TripSage requires:

- secure session handling across RSC + Route Handlers
- clean server/client Supabase client creation
- authorization enforcement at the database boundary

Supabase Auth Helpers are deprecated in favor of `@supabase/ssr`.

## Decision

- Use `@supabase/ssr` to create:
  - a server client (reads cookies, writes refreshed cookies)
  - a browser client (client-side auth functions)
- Enforce authorization in Postgres using RLS policies for every user-facing table.
- Prefer RPC functions for:
  - complex search queries (hybrid RAG search, ranking)
  - multi-table transactional operations where required
- Generate TypeScript DB types via Supabase CLI and commit them to the repo.

## Consequences

- Strong security posture via RLS-first.
- Reduced app-layer authorization bugs.
- Requires explicit RLS and policy testing.

## References

```text
Supabase SSR guide: https://supabase.com/docs/guides/auth/server-side
Creating a Supabase SSR client: https://supabase.com/docs/guides/auth/server-side/creating-a-client
Migrating from auth-helpers to SSR: https://supabase.com/docs/guides/auth/server-side/migrating-to-ssr-from-auth-helpers
Auth helpers deprecation notice: https://github.com/supabase/auth-helpers
```
