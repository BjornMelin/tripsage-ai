# Auth Boundaries and Flow

## Summary

- **Frontend**: Uses `@supabase/ssr` for cookie-based sessions. Client-side CRUD goes directly to Supabase with RLS.
- **API**: Authentication is enforced centrally by `AuthenticationMiddleware` using claims-first verification (`auth.get_claims`). Routes retrieve the authenticated user via principal dependencies.
- **Server-side RLS**: When the API must access PostgREST on behalf of a user, it creates a `postgrest_for_user(token)` client to preserve RLS.

## Key Components

- **Frontend**
  - `frontend/middleware.ts`: refreshes session via `supabase.auth.getUser()` and syncs cookies.
  - `frontend/src/lib/supabase/client.ts` / `server.ts`: `createBrowserClient` / `createServerClient` utilities.
  - `frontend/src/lib/supabase/token.ts`: single source of truth for access tokens.
  - `frontend/src/hooks/use-authenticated-api.ts`: sends `Authorization: Bearer <access_token>` on API calls; preserves server `ApiError` details.

- **Backend**
  - Middleware: `tripsage/api/middlewares/authentication.py` validates JWT with `verify_and_get_claims` and sets `request.state.principal`.
  - Dependencies: `tripsage/api/core/dependencies.py` exposes `get_current_principal` / `require_principal` for routes and services.
  - Supabase clients: `tripsage_core/services/infrastructure/supabase_client.py` provides async clients and `postgrest_for_user(token)`.

## Rules of Engagement

1. Prefer direct supabase-js for read/write operations that are purely RLS-governed and safe to run from the browser.
2. Use the API for business logic, cross-service calls, or any operation needing secrets or additional authorization beyond RLS.
3. The API must not re-verify tokens in route handlers; it reads the principal that the middleware already established.
4. For server-side reads/writes on behalf of a user, obtain a PostgREST client using the user access token to preserve RLS policies.

## References

- Supabase Python `auth.get_claims`: preferred over `get_user` for JWKS-backed verification and performance.
- Supabase SSR: `@supabase/ssr` docs for cookie-based session management.
