# Supabase Auth Inventory (2025-11)

This document captures the current authentication-related touchpoints across the
TripSage monorepo ahead of migrating fully to Supabase-managed auth flows.

## Backend (FastAPI)

- `tripsage/api/middlewares/authentication.py`
  - Single enforcement point for Supabase-issued JWTs. Validates bearer tokens
    via `tripsage_core.services.infrastructure.supabase_client.verify_and_get_claims`
    and populates `request.state.principal`.
- `tripsage/api/routers/auth.py`
  - No custom auth flows. Every endpoint returns `501` with instructions to use
    Supabase-managed signup/sign-in. Prevents regressions into legacy flows.
- `tripsage/api/routers/*`
  - All protected routers rely on the middleware + dependency injection helpers
    from `tripsage.api.core.dependencies` (Principal-based) for per-request user
    context rather than local credential checks.
- `tripsage_core/services/infrastructure/supabase_client.py`
  - Owns creation of Supabase admin/public async clients and JWT verification
    helpers used by both middleware and domain services.
- `tripsage_core/services/business/*`
  - No remaining password hashing or local user stores. All user lifecycle
    logic delegates to Supabase-admin clients fetched above.

## Frontend (Next.js 16 + Supabase SSR)

- `frontend/middleware.ts`
  - Creates a Supabase SSR client via `@supabase/ssr` on each request, refreshes
    cookies, and ensures React Server Components always see a hydrated session.
- `frontend/src/lib/supabase/server.ts`, `client.ts`, `admin.ts`
  - Server factory (`createServerSupabase`) wraps Next `cookies()` store for RSC
    and Route Handlers. Browser factory memoizes a singleton client plus hooks
    (`useSupabase`). Admin factory uses service-role key for SECURITY DEFINER
    RPCs (only from server routes: BYOK, webhooks).
- `frontend/src/hooks/use-authenticated-api.ts`
  - Generates FastAPI-bound requests with fresh Supabase access tokens. Uses
    Supabase session refresh (cookie-based) and supplies `Authorization: Bearer`
    headers for `/api/*` routes.
- `frontend/src/components/providers/realtime-auth-provider.tsx`
  - Keeps Supabase Realtime sockets authorized by syncing `supabase.realtime`
    auth with current access tokens.
- `frontend/src/hooks/use-trips.ts`, `use-supabase-chat.ts`,
  `use-supabase-storage.ts`, `use-supabase-realtime.ts`
  - Read/write Supabase PostgREST tables directly (trips, chat_sessions,
    file_attachments, etc.) and subscribe to realtime channels using the
    browser client. Every hook gates operations on `supabase.auth.getUser()`.
- `frontend/src/stores/auth-store.ts`
  - Still a mocked Zustand store for local prototyping. Not wired into Supabase
    and safe to delete once all screens consume Supabase-authenticated hooks.
- `frontend/src/lib/api/api-client.ts`
  - Pure HTTP client; relies on callers (usually `useAuthenticatedApi`) to set
    Supabase-issued bearer tokens before hitting FastAPI.

## Supabase ↔️ Vercel Webhooks

- `supabase/migrations/20251113034500_webhooks_consolidated.sql`
  - Installs SECURITY DEFINER triggers that call `supabase_functions.http_request`
    with HMAC headers for trips, collaborators, cache-tag tables, chat tables.
- `frontend/src/app/api/hooks/trips|cache/route.ts`
  - Next.js Route Handlers that verify HMAC via `lib/webhooks/payload.ts`,
    dedupe events with Upstash Redis idempotency keys, and either touch Supabase
    (trip collaborators) or bump cache tags. `dynamic = "force-dynamic"` keeps
    them server-only.
- `docs/operators/supabase-webhooks.md`
  - Source of truth for configuring Postgres GUCs (`app.vercel_*` URLs and HMAC
    secrets) and verifying signatures.

## Supabase Vault + BYOK (AI SDK v6)

- `supabase/migrations/20251030000000_vault_api_keys.sql`
  - Enables Vault, creates `public.api_keys`, and exposes SECURITY DEFINER RPCs
    (`insert/get/delete/touch_user_api_key`) for storing encrypted provider keys.
- `supabase/migrations/20251113000000_gateway_user_byok.sql`
  - Adds `api_gateway_configs`, `user_settings`, and RPCs to persist per-user
    Gateway base URLs plus the `allow_gateway_fallback` flag.
- `frontend/src/lib/supabase/rpc.ts`
  - Typed wrappers around the Vault + Gateway RPCs. Always execute using the
    service-role admin client (`lib/supabase/admin.ts`).
- `frontend/src/app/api/keys/*`
  - `/api/keys` POST/GET store metadata + call `insertUserApiKey`, and
    `/api/keys/validate` uses AI SDK clients (`createOpenAI`, `createAnthropic`,
    `createGateway`) to run live model list fetches for key validation with rate
    limiting.
- `frontend/src/app/api/user-settings/route.ts`
  - CRUD for the `user_settings.allow_gateway_fallback` flag; consumed by the
    provider resolver for gating Gateway fallback.
- `frontend/src/lib/providers/registry.ts`
  - Central resolver for AI SDK v6. Reads Supabase Vault keys via RPC wrappers,
    falls back to server env keys, then to the Vercel AI Gateway (if allowed).
    Returns `LanguageModel` instances consumed by chat routes.
- `frontend/src/app/api/chat/route.ts` & `chat/stream/route.ts`
  - Route adapters (non-stream + streaming) that call `createServerSupabase()`
    to grab the authenticated user, apply Upstash rate-limits, resolve providers
    via the registry, and pass dependencies into `_handler.ts`.
- `frontend/src/app/api/chat/_handler.ts` & `chat/stream/_handler.ts`
  - Pure handlers that:
    - Re-check Supabase auth via the injected client.
    - Hydrate user memories from Supabase tables.
    - Validate attachments.
    - Clamp tokens (`lib/tokens/*`).
    - Construct tool registries (planning, booking) and call AI SDK v6
      (`generateText` / `streamText` with `toolRegistry` + `wrapToolsWithUserId`).
    - Persist streamed chat metadata back into Supabase via typed helpers.

## Supabase Database + Storage Touchpoints

- `frontend/src/lib/supabase/database.types.ts`
  - Generated types used across hooks, storage helpers, and typed RPCs.
- `frontend/src/lib/supabase/typed-helpers.ts`
  - Shared helpers for insert/update returning typed rows (`insertSingle`,
    `updateSingle`) to avoid `any` casts when working with PostgREST responses.
- `frontend/src/hooks/use-supabase-storage.ts`
  - Wraps Supabase Storage upload/download + `file_attachments` table writes and
    exposes progress-aware hooks for React components.
- `frontend/src/hooks/use-supabase-chat.ts`
  - Direct Supabase CRUD + realtime subscriptions for chat sessions/messages/tool
    calls, bridging the AI chat UI with persisted state.
- `frontend/src/lib/tools/*`
  - Server-only tools invoked by AI SDK (planning, memory). They use
    `createServerSupabase()` to enforce RLS when reading/writing tables.

## Documentation + Config Status

- `docs/architecture/frontend-architecture.md` and this file are the canonical
  references for Supabase/Next integration.
- `.env.example` / `frontend/.env.example` now require only Supabase URL + keys,
  Upstash Redis creds, and provider keys; no custom JWT secrets remain.
- Legacy docs (`docs/api/auth.md`) still mention TripSage-managed tokens—open
  TODO to rewrite them to reference Supabase-only flows.

## Current Gaps / Follow-ups

1. `frontend/src/stores/auth-store.ts` is still mocked; migrate remaining UI to
   Supabase session-aware hooks and delete the store.
2. Documentation around backend FastAPI endpoints (`docs/api/auth.md`) must be
   updated to emphasize Supabase-only login flows.
3. Finish backfilling Supabase-focused runbooks for BYOK (CLI steps, Vault key
   rotations) so the README no longer references removed scripts.
