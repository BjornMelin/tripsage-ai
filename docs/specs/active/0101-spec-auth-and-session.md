# SPEC-0101: Authentication and session (Supabase SSR + RLS)

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

## Goals

- Supabase auth works in:
  - Server Components
  - Route Handlers
  - Client components
- Session is available for SSR and refreshed via secure cookies.
- Authorization is enforced via RLS policies.

## Requirements

### Client creation

- Server client uses `@supabase/ssr` and Next cookies integration.
- Browser client uses `@supabase/supabase-js`.

### Auth flows

- Email/password and OAuth (configurable).
- Protected routes under `src/app/app/*`.
- Redirect unauthenticated users to login.

### RLS baseline

- Every user-scoped table must have:
  - RLS enabled
  - a `user_id` or membership table
  - policies for select/insert/update/delete
- Use service role key only in server-only contexts and never in client bundles.

## Data model (minimum)

- users: Supabase auth users
- profiles: public profile data (1:1 with auth.users)
- memberships: (user_id, trip_id, role)

## Testing

- Unit tests for server helpers (cookie parsing, client creation).
- E2E login and protected route checks.

## References

```text
Supabase SSR guide: https://supabase.com/docs/guides/auth/server-side
Creating SSR client: https://supabase.com/docs/guides/auth/server-side/creating-a-client
Migrating from auth-helpers: https://supabase.com/docs/guides/auth/server-side/migrating-to-ssr-from-auth-helpers
```
