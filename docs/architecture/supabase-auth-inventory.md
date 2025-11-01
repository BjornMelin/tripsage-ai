# Supabase Auth Inventory (2025-10)

This document captures the current authentication-related touchpoints across the
TripSage monorepo ahead of migrating fully to Supabase-managed auth flows.

## Backend (FastAPI)

- `tripsage/api/middlewares/authentication.py`
  - Performs dual-mode auth: custom JWT validation (HS256 using
  - Populates `request.state.principal` and emits audit events.
- `tripsage/api/routers/auth.py`
  - Exposes legacy `/api/auth/register` endpoint that proxies to
    `UserService`. No Supabase integration today.
- `tripsage/api/routers/keys.py`
  - Still used by frontend hooks (`useApiKeys`), independent from Supabase auth.
- `tripsage/api/core/dependencies.py`
- `tripsage_core/services/infrastructure/supabase_client.py`
  - Provides admin/public Supabase clients and `verify_and_get_claims(jwt)` which
    wraps `supabase.auth.get_claims`.
- `tripsage_core/services/business/user_service.py`
  - Maintains local user registration, password hashing, and login utilities
    (via `passlib`). This duplicates Supabase functionality.
- `tripsage_core/services/business/api_key_service.py`
    from Supabase; used by `/api/keys`.
- `tripsage_core/services/business/auth_service.py`
  - Supplies FastAPI dependencies that call `verify_and_get_claims`. Currently a
    partial bridge to Supabase but still wrapped by legacy middleware.

## Frontend (Next.js 16)

- `frontend/middleware.ts`
  - Uses `@supabase/ssr` `createServerClient` to refresh sessions on each
    request. Matches Supabase cookie-based best practices.
- `frontend/src/lib/supabase/client.ts` & `server.ts`
  - Create browser/server Supabase clients via `@supabase/ssr`.
- `frontend/src/hooks/use-authenticated-api.ts`
  - Fetches Supabase session tokens manually (`getSession` + `refreshSession`)
    and forwards as Bearer tokens to FastAPI.
- `frontend/src/stores/auth-store.ts`
  - Contains mocked login/register/password flows that do **not** call Supabase.
  - Maintains local `tokenInfo`/`session` state separate from Supabase cookie
    sessions.
- `frontend/src/hooks/use-trips-supabase.ts`, `use-supabase-storage.ts`,
  `use-supabase-chat.ts`
  - Query Supabase directly using `supabase.auth.getUser()` and
    `onAuthStateChange` listeners.
- `frontend/src/lib/api/client.ts`
  - Expects callers to supply `auth` header (currently provided by
    `useAuthenticatedApi`).

## Supabase Edge Functions & Utilities

- `supabase/functions/_shared/supabase.ts`
  - Provides `createUserClient` and `validateAuth` using Supabase Admin auth.
- `supabase/functions/*`
  - Edge functions validate incoming requests via Supabase admin client.

## Documentation + Config

- `docs/architecture/auth-boundaries.md`
- `docs/api/auth.md`
  - Still references TripSage JWT issuance and token refresh flows.
- Environment variables in `.env.example` & `pyproject.toml` depend on `passlib`
  and custom secrets (`database_jwt_secret`).

## Observations

1. Authentication middleware now exclusively relies on Supabase JWT claim verification.
2. Frontend SSR middleware aligns with Supabase cookies, but local auth stores still mirror legacy token logic.
3. BYOK/API key modules and routes were removed; future integrations should prefer Supabase secrets or provider-native flows.
4. Documentation still references the retired API key system and needs a follow-up pass.
