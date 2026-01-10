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

- Server client uses `@supabase/ssr` and Next `cookies()` integration:
  - `src/lib/supabase/server.ts` (`createServerSupabase()`)
  - `src/lib/supabase/factory.ts` (`createServerSupabaseClient()`, `createMiddlewareSupabase()`)
- Browser client uses `@supabase/ssr` `createBrowserClient()` (typed singleton):
  - `src/lib/supabase/client.ts` (`getBrowserClient()`, `useSupabaseRequired()`)
- Service role client is server-only:
  - `src/lib/supabase/admin.ts` (`getAdminSupabase()` / `createAdminSupabase()`)

### Session refresh (SSR cookies)

- Use Next.js Proxy to refresh Supabase session cookies for Server Components:
  - `src/proxy.ts` (`proxy()`), built on `createMiddlewareSupabase()` + `getCurrentUser()`.
- Proxy is also the canonical location for CSP nonce + baseline security headers (see SPEC-0108).

### Auth flows

- Email/password and OAuth (configurable).
- Email/password uses Server Actions (credentials never hit client bundles):
  - `src/lib/auth/actions.ts` (`loginWithPasswordAction`, `registerWithPasswordAction`, `logoutAction`)
  - `src/components/auth/login-form.tsx`, `src/components/auth/register-form.tsx`
- OAuth uses browser client redirect flows from the auth forms.
- Logout:
  - Server Action: `src/lib/auth/actions.ts` (`logoutAction`)
  - Route handler: `src/app/auth/logout/route.ts` (GET/POST `/auth/logout`)
- Protected routes live under `src/app/(app)/*` and must redirect unauthenticated users to `/login`.

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

- Unit tests for server helpers (cookie parsing, client creation): `src/lib/supabase/__tests__/*`.
- Auth action tests: `src/lib/auth/__tests__/*`.
- E2E login and protected route checks (Playwright): `e2e/*` (when present).

## References

```text
Supabase SSR guide: https://supabase.com/docs/guides/auth/server-side
Creating SSR client: https://supabase.com/docs/guides/auth/server-side/creating-a-client
Migrating from auth-helpers: https://supabase.com/docs/guides/auth/server-side/migrating-to-ssr-from-auth-helpers
```
