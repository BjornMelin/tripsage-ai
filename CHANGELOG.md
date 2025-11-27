# Changelog

All notable changes to TripSage will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_No unreleased changes yet._

## [1.1.0] - 2025-11-25

### Security

- Replaced insecure ID generation: migrated all `Date.now().toString()` and direct `crypto.randomUUID()` usage to `secureUuid()` from `@/lib/security/random` in stores, components, API routes, and AI tools.
- Removed `Math.random()` from production code: replaced with deterministic values in backup code verification and agent collaboration hub performance simulation.
- Removed `console.*` statements from server modules: replaced development logging and error fallbacks in `lib/api/api-client.ts`, `lib/error-service.ts`, and `lib/cache/query-cache.ts` with telemetry helpers or silent error handling per AGENTS.md compliance.

### Added

- **Nuclear Auth Integration (Dashboard)**:
  - `DashboardLayout` converted to a Server Component using `@/lib/auth/server` helpers (`requireUser`, `mapSupabaseUserToAuthUser`) for secure, waterfall-free user data fetching.
  - `logoutAction` Server Action (`src/lib/auth/actions.ts`) for secure, cookie-clearing logout flows via Supabase SSR.
  - `SidebarNav` and `UserNav` extracted to standalone Client Components with improved active-route highlighting (nested route support) and real user data display.

- Personalization Insights page now surfaces recent memories with localized timestamps, source/score, and copyable memory IDs using the canonical memory context feed.
- Testing patterns companion guide (`docs/development/testing.md`) with test-type decision tree plus MSW and AI SDK v6 examples.
- Supabase local config: added `project_id`, `[db.seed]` configuration, and `[storage.buckets.attachments]` bucket definition with MIME type restrictions in `supabase/config.toml`.
- Supabase-backed agent configuration control plane: new `agent_config` and `agent_config_versions` tables with admin-only RLS, upsert RPC, and schema types wired into the codebase.
- Configuration resolver with Upstash cache + Zod validation and coverage, plus authenticated API routes (`GET/PUT /api/config/agents/:agentType`, versions listing, rollback) using `withApiGuards`, telemetry, and cache-tag invalidation.
- Admin Configuration Manager rebuilt to server-first data access; displays live config, version history, and rollback via the new APIs.
- All AI agents (budget, destination, flight, itinerary, accommodation, memory) now load model/temperature/token limits from centralized configuration before calling `streamText` (see ADR-0052: `docs/adrs/adr-0052-agent-configuration-backend.md` for architecture details).
- Document Supabase memory orchestrator architecture and implementation plan (ADR-0042, SPEC-0026, database/memory prompt).
- Add Next.js 16 trip domain API routes (`/api/trips`, `/api/trips/suggestions`, `/api/itineraries`, `/api/dashboard`) backed by Supabase SSR, Zod v4 schemas, unified `withApiGuards` auth/rate limiting, and AI SDK v6 structured trip suggestions.
- Add `src/lib/ai/tool-factory.ts` with typed telemetry/cache/rate-limit guardrails plus coverage in `src/lib/ai/tool-factory.test.ts`, establishing a single `createAiTool` entrypoint for all tools.
- Upstash testing harness (`frontend/src/test/setup/upstash.ts`, `frontend/src/test/msw/handlers/upstash.ts`, smoke scaffolds in `frontend/src/test/upstash/`) provides shared Redis/ratelimit stubs and MSW handlers to mock rate limiting and cache/Redis unavailability without external dependencies; includes smoke-test scaffold. See ADR-0054 and SPEC-0032 for the tiered strategy.
- Security dashboard and MFA flows: added security dashboard UI plus MFA setup/verification and backup-code components, along with realtime connection status monitor.
- Flights: new `/api/flights/popular-destinations` route with Supabase-personalized results, Upstash caching (1h TTL), and route rate limiting.
- Authenticated account deletion route `/auth/delete` uses Supabase admin `deleteUser` with service-role guardrails.
- Security session APIs: added `GET /api/security/sessions` and `DELETE /api/security/sessions/[sessionId]` with admin Supabase access, `withApiGuards` telemetry/rate limits (`security:sessions:list`, `security:sessions:terminate`), and Vitest coverage for listing/termination flows.
- Security events and metrics APIs: added `/api/security/events` and `/api/security/metrics` with Supabase admin queries, strict Zod schemas, OTEL telemetry, and rate limits (`security:events`, `security:metrics`) powering the dashboard.
- Google Places autocomplete now covered by MSW handlers and Vitest component tests for happy path, type filtering, rate limit errors, and latest-query guarding in `frontend/src/components/features/search/destination-search-form`.

- Dashboard metrics API with Redis caching and OpenTelemetry tracing
- Dashboard metrics visualization components using Recharts
- API metrics recording infrastructure with Supabase persistence
- Centralized dashboard metrics schemas

### Changed

- Supabase realtime store hardening: serialized `reconnectAll` with `isReconnecting`, awaited channel resubscribe/unsubscribe, memoized `summary()`, and narrowed status typing to the Supabase channel state union.
- Connection status monitor now uses camelCase helper naming and shallow selector to avoid unnecessary re-renders.
- Supabase realtime hook `useSupabaseRealtime` now wraps `reconnect` to pull the latest store implementation, preventing stale references.
- Activities search page comparison flow now bases modal open/close logic on post-toggle selection counts, replaces transition-wrapped Promise with explicit pending state, and keeps trip modal add flow consistent.
- Trip selection modal resets selection on close/activity change and makes the “Create a new trip” button navigate to `/trips`.
- MFA setup mock path now throws in non-development environments to avoid implying production MFA enablement.
- Logout server action uses scoped telemetry logger and catches sign-out errors before redirecting.
- Realtime API docs now list the full status enum (`idle/connecting/subscribed/error/closed`) and architecture docs describe the app-level statuses (`connecting | connected | disconnected | reconnecting | error`).
- **Dashboard Architecture**: Refactored `DashboardLayout` to a Server Component architecture, removing `use client` and eliminating client-side auth waterfalls.

- README updated for production run port 3000, AI Gateway/Supabase env variables (`NEXT_PUBLIC_SUPABASE_*`, `DATABASE_SERVICE_KEY`, `AI_GATEWAY_API_KEY`), and security/audit commands (`pnpm audit`, `pnpm test:run --grep security`).
- Migrated Next.js middleware to proxy: replaced `frontend/middleware.ts` with `frontend/src/proxy.ts` per Next.js 16 (ADR-0013).
- Added Turbopack file system cache: enabled `turbopackFileSystemCacheForDev` in `next.config.ts` for faster dev builds.
- Updated Turbopack root config: set `turbopack.root` to `"."` in `next.config.ts`.
- Refactored trips API route: replaced inline `mapTripRowToUi` with shared `mapDbTripToUi` mapper.
- Supabase config modernization: removed deprecated `storage.image_transformation`, fixed Inbucket ports to defaults (54324-54326), updated `api.extra_search_path` to `["public", "extensions"]`, set `edge_runtime.policy` to `"oneshot"` for development hot reload, and fixed `edge_runtime.inspector_port` to default 8083 in `supabase/config.toml`.
- Supabase dependencies: upgraded `@supabase/supabase-js` and `@supabase/postgrest-js` from `2.80.0` to `2.84.0`; verified type compatibility and API usage patterns remain unchanged.
- Removed `frontend/src/domain/schemas/index.ts` barrel and updated all imports to use file-scoped schema modules via `@schemas/*`, eliminating circular dependencies and improving Next.js tree-shaking.
- Renamed aliased exports referenced from the old schema barrel to canonical symbol names in their source files (for example, configuration and validation error schemas in `frontend/src/domain/schemas/*.ts`) so all callers import the final names directly.
- Rewired higher-level agents in `frontend/src/lib/agents/*` to consume tools from the centralized `@ai/tools` registry and its `toolRegistry` export, replacing the previous `@/lib/tools` indirection.
- **Provider migration: Expedia Rapid → Amadeus + Google Places + Stripe**
  - Destination search now uses Google Places Text Search with debounced queries, normalized limits, and a shared results store; the destination search form uses the new hook.
  - Activities search page uses the real activity search hook, surfaces loading/error states, and opens booking targets via `openActivityBooking`.
  - Expedia schemas consolidated into `frontend/src/domain/schemas/expedia.ts` and domain paths updated; accommodations tools, booking payments, and tests now import the domain client and types, removing the legacy `frontend/src/lib/travel-api` path.
  - Accommodation guardrails now preserve the original provider name instead of reporting `"cache"` on cached results, and surface 429/404 responses as explicit availability codes instead of cache hits—improving client clarity and error handling. Booking confirmations still fall back to generated references when Expedia omits a confirmation number.
- Migrated all AI tool tests from `frontend/src/lib/tools/__tests__` into `frontend/src/ai/tools/server/__tests__`, aligning test locations with the canonical tool implementations in `frontend/src/ai/tools/server/*.ts`.
- Derive rate-limit identifiers inside `createAiTool` via `headers()` with `x-user-id` → `x-forwarded-for` fallback, sanitize overrides, and expand unit tests to cover the new helper (`frontend/src/lib/ai/tool-factory*.ts`).
- Remove `runWithGuardrails` runtime + tests, rewrap memory writes through `createAiTool`, and normalize memory categories before caching/telemetry (`frontend/src/lib/agents/memory-agent.ts`, `frontend/src/lib/agents/__tests__/memory-agent.test.ts`, `frontend/src/lib/agents/runtime.ts`).
- Centralized tool error helpers in `frontend/src/ai/tools/server/errors.ts` and updated all tools and agents to import `TOOL_ERROR_CODES` / `createToolError` from `@ai/tools/server/errors`; removed the legacy `frontend/src/lib/tools/errors.ts` module.
- Moved travel planning tools and schemas to `frontend/src/ai/tools/server/planning.ts` and `frontend/src/ai/tools/server/planning.schema.ts`, and migrated their tests to `frontend/src/ai/tools/server/__tests__/planning.test.ts`; deleted the old `frontend/src/lib/tools/planning*.ts` files.
- Replaced `frontend/src/lib/tools/travel-advisory.ts` and its helpers with `frontend/src/ai/tools/server/travel-advisory.ts` plus `frontend/src/ai/tools/server/travel-advisory/**` (providers, utilities, tests) backed by the U.S. State Department Travel Advisories API.
- Replaced `frontend/src/lib/tools/injection.ts` with `frontend/src/ai/tools/server/injection.ts` and updated the chat stream handler to inject `userId`/`sessionId` via `wrapToolsWithUserId` from `@ai/tools/server/injection`.
- Trip Type Architecture: Unified type definitions into `@schemas/trips` as the canonical source (see Removed section at lines 130–131 for cleanup context).
- Consolidated Trip type definitions: canonical `UiTrip` type now defined in `@schemas/trips` (`storeTripSchema`); stores and hooks import and re-export for convenience. Removed duplicate Trip type definitions from `domain/schemas/api.ts`. Database type `Trip = Tables<"trips">` remains separate in `database.types.ts` for raw DB row representation.
- Consolidated TripSuggestion types: removed duplicate interface from `hooks/use-trips.ts`; all consumers now use `TripSuggestion` from `@schemas/trips`.
- **React 19 login form modernization**: Refactored email/password login to use server actions with `useActionState`/`useFormStatus` for progressive enhancement, replacing route-based redirects with inline error handling and pending states. Created `loginAction` server action in `frontend/src/app/(auth)/login/actions.ts` with Zod validation, Supabase SSR authentication, and safe redirect logic. Updated `frontend/src/components/auth/login-form.tsx` to use React 19 hooks with field-specific error rendering and `SubmitButton` component. Converted `/auth/login` route to thin wrapper for external API compatibility while maintaining all security safeguards. Added comprehensive tests in `frontend/src/app/(auth)/login/__tests__/actions.test.ts` covering validation, authentication, and redirect scenarios.
- **AI SDK v6 Tool Migration**: Complete refactoring of tool architecture to fully leverage AI SDK v6 capabilities. Migrated `createAiTool` factory to remove type assertions, properly integrate ToolCallOptions with user context extraction from messages, consolidate guardrails into single source of truth, eliminate double-wrapping in agent tools, and update all 18+ tool definitions to use consistent patterns. Enhanced type safety with strict TypeScript compliance, improved test coverage using AI SDK patterns, and eliminated code duplication between tool-factory and guarded-tool implementations. Added comprehensive documentation in `docs/development/ai-tools.md` for future tool development.
- **Configuration and dependency updates**: Enabled React Compiler and Cache Components in Next.js 16; updated Zod schemas to v4 APIs (z.uuid(), z.email(), z.int()); migrated user settings to Server Actions with useActionState; consolidated Supabase client imports to @/lib/supabase; unified Next.js config files into single next.config.ts with conditional bundle analyzer; added jsdom environment declarations for tests; removed deprecated Next.js config keys and custom webpack splitChunks.
- **Chat memory syncing (frontend)**: Rewired `frontend/src/stores/chat/chat-messages.ts` to call `useChatMemory` whenever messages are persisted, trigger `/api/memory/sync` after assistant responses, skip system/placeholder entries, and keep `currentSession` derived from store state; updated slice tests (`frontend/src/stores/__tests__/chat/chat-messages.test.ts`) accordingly.
- **Tool guardrails unification**: Replaced bespoke wrappers with `createAiTool` for Firecrawl web search (`frontend/src/lib/tools/web-search.ts`) and accommodation agent helpers (`frontend/src/lib/agents/accommodation-agent.ts`), consolidating caching, rate limiting, and telemetry. Updated `frontend/src/lib/tools/__tests__/web-search.test.ts` plus shared test utilities (`frontend/src/test/api-test-helpers.ts`) to exercise the new factory behavior.
- Refactored flight and weather tooling to static `createAiTool` exports with guardrails, schema-aligned inputs, updated agents, and refreshed unit tests (`frontend/src/lib/tools/{flights,weather}.ts`, `frontend/src/lib/agents/{flight,destination}-agent.ts`, `frontend/src/lib/tools/__tests__/{flights,weather}.test.ts`).
- Centralized agent workflow schemas in `frontend/src/domain/schemas/agents.ts` and updated all agent, tool, route, prompt, and UI imports to use the `@schemas/agents` alias instead of the removed `frontend/src/lib/schemas` registry.
- Co-located weather tool input and result schemas in `frontend/src/ai/tools/schemas/weather.ts` and updated `frontend/src/ai/tools/server/weather.ts` to consume these types directly, removing the legacy `@/lib/schemas/weather` dependency.
- Tightened TypeScript coverage for agent result UI components (`BudgetChart`, `DestinationCard`, `FlightOfferCard`, `StayCard`, and `ItineraryTimeline`) and `frontend/src/lib/agents/memory-agent.ts` by replacing implicit `any` usage with precise types derived from domain and tool schemas.

- Testing guide expanded with MSW, AI SDK v6, fake-timer, factory, and CI guidance; consolidated React Query helpers to `@/test/query-mocks` and removed legacy `test/mocks/react-query.ts`; `test:ci` now uses the threads pool.
- **Auth store security hardening (Supabase SSR-aligned)**
  - Removed client-side persistence of access/refresh tokens from `frontend/src/stores/auth/auth-session.ts`; the slice now exposes only session view state (`session`, `sessionTimeRemaining`) with `setSession` / `resetSession`, treating Supabase SSR cookies as the sole session authority.
  - Updated `frontend/src/stores/auth/auth-core.ts` logout to call the session slice’s `resetSession()` action instead of manually mutating token/session fields, ensuring logout consistently clears local auth-session state.
- **Supabase-first auth flows (frontend)**
  - Added Supabase SSR-backed login, register, and logout route handlers under `frontend/src/app/auth/{login,register,logout}/route.ts` that use `createServerSupabase()` and Zod form schemas, eliminating client-side `supabase.auth.signInWithPassword`/`signUp` calls for core flows.
  - Rewired `frontend/src/components/auth/{login-form,register-form}.tsx` to post HTML forms to the new `/auth/*` routes and surface server-side validation/auth errors via query parameters instead of local state.
  - Introduced a safe redirect helper in `frontend/src/app/auth/login/route.ts` to guard against protocol-relative open redirects when handling `redirectTo`/`next` parameters.
- **Auth store reset orchestration (Wave B)**
  - Centralized auth-core and auth-validation default view-model state in `frontend/src/stores/auth/auth-core.ts` (`authCoreInitialState`) and `frontend/src/stores/auth/auth-validation.ts` (`authValidationInitialState`) to keep tests and runtime behavior aligned.
  - Added `frontend/src/stores/auth/reset-auth.ts` with `resetAuthState()` to reset auth-core, auth-session, and auth-validation slices in one call, including clearing persisted auth-core storage for Supabase SSR-aligned logout flows and test setup.
  - Updated auth store tests under `frontend/src/stores/__tests__/auth/` to exercise `resetAuthState()` and assert that `logout()` invokes the session slice’s `resetSession()` action, and adjusted email verification tests to expect errors via the `registerError` field.
- **Auth core view-model finalization (Wave C)**
  - Simplified `frontend/src/stores/auth/auth-core.ts` to a pure view-model over the current `AuthUser` snapshot and Supabase SSR session initialization/logout, removing unused login/register and profile mutation methods and all `/api/auth/*` references from the store.
  - Confirmed profile management is handled exclusively by `frontend/src/stores/user-store.ts`, keeping auth-core focused on authentication-derived state instead of user profile editing concerns.
  - Updated `frontend/src/stores/__tests__/auth/auth-core.test.ts` to validate the slimmer auth-core API (initialization, logout, setUser, error handling, display name, and `resetAuthState()` orchestration) and removed tests tied to the legacy `/api/auth/*` mutation methods.
- **Auth guards and protected routes (Wave D)**
  - Enforced Supabase SSR authentication for all dashboard routes via `frontend/src/app/(dashboard)/layout.tsx`, which now calls `requireUser()` before rendering the client-side `DashboardLayout`.
  - Added server layouts for `frontend/src/app/settings` and `frontend/src/app/chat` that call `requireUser()` (with `redirectTo` set to `/settings` and `/chat` respectively), ensuring settings and chat UIs are evaluated per request and gated by Supabase cookies.
  - Guarded the attachments listing page in `frontend/src/app/attachments/page.tsx` by calling `requireUser({ redirectTo: "/attachments" })` ahead of the SSR fetch to `/api/attachments/files`.
  - Updated AI/LLM and chat-related API routes to require authentication via `withApiGuards({ auth: true, ... })` for `/api/chat`, `/api/chat/stream`, `/api/chat/attachments`, `/api/agents/router`, and `/api/agents/itineraries`, while keeping the minimal `/api/ai/stream` demo and internal embeddings/route-matrix endpoints as explicitly non-authenticated where existing non-Supabase guards apply.
  - Added unit tests for `frontend/src/lib/auth/server.ts` in `frontend/src/lib/auth/__tests__/server.test.ts` to verify `getOptionalUser` behavior, successful `requireUser` when a user is present, and redirect-to-login behavior when unauthenticated (matching `/login?next=/dashboard` semantics).
- **Legacy auth cleanup and tests (Wave E)**
  - Removed the shared Supabase access token helper `frontend/src/lib/supabase/token.ts` and inlined its behavior into `frontend/src/components/providers/realtime-auth-provider.tsx`, keeping Realtime authorization ephemeral and aligned with cookie-based session authority.
  - Updated `frontend/src/__tests__/realtime-auth-provider.test.tsx` to rely on the Supabase browser client mock directly instead of mocking the deleted token helper.
- **Supabase SSR auth validation and observability**
  - Added dedicated route tests for `/auth/login`, `/auth/register`, `/auth/logout`, and `/auth/me` under `frontend/src/app/auth/**/__tests__/route.test.ts` to exercise the Supabase SSR-backed flows and `lib/auth/server.ts` helpers.
- Simplified `frontend/src/hooks/use-authenticated-api.ts` to use the shared `apiClient` directly without Supabase JWT or refresh-session management, relying on Supabase SSR cookie sessions and `withApiGuards` as the sole authentication mechanism for `/api/*` routes.
- **Telemetry helpers consolidation (frontend)**: Extended `frontend/src/lib/telemetry/span.ts` with `addEventToActiveSpan`, `recordErrorOnSpan`, and `recordErrorOnActiveSpan` helpers, and updated webhook payload handling (`frontend/src/lib/webhooks/payload.ts`) and file webhook route (`frontend/src/app/api/hooks/files/route.ts`) to use these helpers instead of calling `@opentelemetry/api` directly.
- **Client error reporting telemetry**: Added `frontend/src/lib/telemetry/client-errors.ts` and rewired `frontend/src/lib/error-service.ts` so browser error reports record exceptions on the active OpenTelemetry span via `recordClientErrorOnActiveSpan` instead of reading `trace.getActiveSpan()` inline.
- Flight search form now fetches popular destinations via TanStack Query from `/api/flights/popular-destinations`, shows loading/error states, and uses real backend data instead of inline mocks.
- Security dashboard: cleaned up terminate-session handler placeholder to a concise doc comment, keeping the component free of unused async scaffolding.
- Account settings now calls Supabase Auth for email updates, surfaces verification state with resend support, and persists notification toggles to user metadata with optimistic UI updates.
- Security dashboard now loads active sessions from the new `/api/security/sessions` endpoint, updates metrics from live data, and surfaces toast errors on load failures.
- Security dashboard rebuilt as a server component consuming live events/metrics/sessions endpoints with no client mocks or useEffect fetching.
- Fixed `TripSuggestion` type export: exported from `use-trips.ts` to resolve component import errors.
- Fixed email verification state: removed invalid `profile?.isEmailVerified` reference in account settings.
- Fixed optimistic trip updates types: changed `Trip` references to `UiTrip` from `@schemas/trips`.
- Fixed trip export test: added missing `currency` property to mock trip data.
- Fixed security dashboard import: wrapped server component in dynamic import with Suspense.
- Fixed admin configuration page: added `"use cache: private"` directive to prevent build-time env var errors.
- Removed unused `TripsRow` import from trips API route.
- Trip schema consolidation: added `currency TEXT NOT NULL DEFAULT 'USD'` column to `trips` table in base migration; updated `tripsRowSchema`, `tripsInsertSchema`, `tripsUpdateSchema` to use `primitiveSchemas.isoCurrency`; updated `mapDbTripToUi` to read currency from database row instead of hardcoded value; added currency to trip creation payload mapping in `/api/trips` route handler.
- Test factory cleanup: removed all legacy snake_case field support (`user_id`, `start_date`, `end_date`, `created_at`, `updated_at`) from `trip-factory.ts`; factory now uses camelCase fields exclusively; updated `database.types.ts` to include currency in trips Row/Insert/Update types.

- Centralized store validation schemas to @schemas/stores
- Updated dashboard page to include metrics visualization
- Integrated metrics recording into API route factory
- Updated test imports and expectations
- Formatted activities page comments and objects

### Removed

- Deleted obsolete `docs/gen_ref_pages.py` MkDocs generator script (Python reference autogen no longer used).
- Deleted legacy schema and tool barrels `frontend/src/lib/schemas/index.ts` and `frontend/src/lib/tools/index.ts`, plus unused compatibility helpers and tests under `frontend/src/lib/tools/{constants.ts,__tests__}`, as part of the final migration to `src/domain` and `src/ai` as the single sources of truth for validation and tooling.
- Removed deprecated `StoreTrip` type alias from `frontend/src/domain/schemas/trips.ts`; all references now use `UiTrip` directly.
- Removed backward compatibility comments from `frontend/src/stores/trip-store.ts` and `frontend/src/hooks/use-trips.ts`; type aliases retained for convenience without compatibility messaging.

- **Backend AI SDK v5 Legacy Code (FINAL-ONLY Cleanup)**

  - Deleted broken router imports: removed `config` and `memory` routers from `tripsage/api/routers/__init__.py` and `tripsage/api/main.py`
  - Removed dead code paths: deleted `ConfigurationService` and `MemoryService` references from `tripsage/app_state.py`
  - Fixed broken memory code: removed undefined variable usage in `tripsage/api/routers/trips.py::get_trip_suggestions`
  - Removed legacy model field: deleted `chat_session_id` from `tripsage_core/models/attachments.py` (frontend handles chat sessions)
  - Deleted superseded tests: removed `tests/unit/test_config_mocks.py` and `tests/integration/api/test_config_versions_integration.py`
  - Cleaned legacy comments: removed historical migration context, updated to reflect current state
  - Backend is now a data-only layer; all AI orchestration is handled by frontend AI SDK v6

- **Vault Ops Hardening Verification (Technical Debt Resolution)**
- Created comprehensive verification documentation: `docs/operations/security-guide.md` with step-by-step security verification process and vault hardening checklist
  - Verified all required migrations applied: vault role hardening, API key security, Gateway BYOK configuration
  - Established operational runbook for staging/production deployment verification
  - Resolved privilege creep prevention measures for Vault RPC operations

### Refactored

- **API route helpers standardization**: Extracted `parseJsonBody` and `validateSchema` helpers to `frontend/src/lib/next/route-helpers.ts` and applied across 30+ API routes, eliminating duplicate JSON parsing and Zod validation code. Standardized error responses (400 for malformed JSON, formatted Zod errors) while preserving route-specific behaviors (custom telemetry, error formats).
- **Backend Cleanup**: Removed legacy AI code superseded by frontend AI SDK v6 migration

  - Deleted `tripsage_core/services/configuration_service.py`
  - Removed agent config endpoints and schemas
  - Cleaned chat-related database methods
  - Removed associated tests
  - Backend now focuses on data persistence; AI orchestration moved to frontend

- **Chat Realtime Stack Simplification (Phase 2)**: Refactored chat realtime hooks and store to be fully library-first and aligned with Option C+ architecture.
  - Refactored `useWebSocketChat` to use `useRealtimeChannel`'s `onMessage` callback pattern instead of direct channel access, eliminating direct `supabase.channel()` calls.
  - Removed legacy WebSocket types (`WebSocketMessageEvent`, `WebSocketAgentStatusEvent`) and replaced with Supabase Realtime payload types (`ChatMessageBroadcastPayload`, `ChatTypingBroadcastPayload`, `AgentStatusBroadcastPayload`).
  - Refactored `chat-store.ts` to be hook-driven: removed `connectRealtime` and `disconnectRealtime` methods that directly managed Supabase channels. Store now exposes `setChatConnectionStatus`, `handleRealtimeMessage`, `handleAgentStatusUpdate`, `handleTypingUpdate`, and `resetRealtimeState` methods.
  - Updated `useSupabaseRealtime` wrappers (`useTripRealtime`, `useChatRealtime`) to use `connectionStatus` from `useRealtimeChannel` instead of deprecated `isConnected` property.
  - Rewrote chat realtime tests to be deterministic with proper mocking of `useRealtimeChannel`, achieving 100% branch coverage for new store methods.
  - Eliminated all deprecated/compat/shim/TODO patterns from chat domain hooks and stores.
- **Agent Status Realtime Rebuild (Phase 3)**: Replaced all direct `supabase.channel()` usage with `useRealtimeChannel` inside `useAgentStatusWebSocket`, wired shared exponential backoff, removed demo-only monitoring props/mocks from `app/(dashboard)/agents/page.tsx`, and added deterministic Vitest coverage for the store/hook/dashboard (100% branch coverage within the agent status scope).

  - Introduced a normalized `useAgentStatusStore` with agent-id maps, connection slice, and explicit APIs (`registerAgents`, `updateAgentStatus`, `updateAgentTask`, `recordActivity`, `recordResourceUsage`, `setAgentStatusConnection`, `resetAgentStatusState`) while deleting session-era helpers.
  - Removed the unused `use-agent-status` polling hook plus dashboard mock data, so agent dashboards now bind directly to the store + realtime hook with zero demo/test-only branches.
  - Added focused tests: `frontend/src/stores/__tests__/agent-status-store.test.ts`, `frontend/src/hooks/__tests__/use-agent-status-websocket.test.tsx`, and `frontend/src/components/features/agent-monitoring/__tests__/agent-status-dashboard.test.tsx` covering all new branches at 100% coverage.

- **Supabase Factory Unification**: Merged fragmented client/server creations into unified factory (`frontend/src/lib/supabase/factory.ts`) with OpenTelemetry tracing, Zod env validation, and `getCurrentUser` helper, eliminating 4x duplicate `auth.getUser()` calls across middleware, route handlers, and pages (-20% auth bundle size, N+1 query elimination).
  - Unified factory with server-only directive and SSR cookie handling via `@supabase/ssr`
  - Integrated OpenTelemetry spans for `supabase.init` and `supabase.auth.getUser` operations with attribute redaction
  - Zod environment validation via `getServerEnv()` ensuring no config leaks
  - Single `getCurrentUser(supabase)` helper used across middleware, server components, and route handlers
  - Comprehensive test coverage in `frontend/src/lib/supabase/__tests__/factory.spec.ts`
  - Updated files: `middleware.ts`, `lib/supabase/server.ts`, `lib/supabase/index.ts`, `app/(auth)/reset-password/page.tsx`
  - Removed all legacy backward compatibility code and exports
- **Supabase Frontend Surface Normalization**: Standardized frontend imports to use `@/lib/supabase` as the single entrypoint for Supabase clients and helpers, replacing direct `@/lib/supabase/server` imports across route handlers, auth pages, tools, and tests.
  - Server code now imports `createServerSupabase` and `TypedServerSupabase` from `frontend/src/lib/supabase/index.ts` instead of internal modules
  - Middleware, calendar helpers, and BYOK API handlers use `createMiddlewareSupabase`/`getCurrentUser` from the same entrypoint for consistent SSR auth wiring
  - Tests updated to mock `@/lib/supabase` where appropriate, keeping Supabase integration details behind the barrel module
- Vitest config now enforces `pool: "threads"` across all projects and relies on per-project includes, improving CPU-bound test throughput while keeping project-scoped patterns intact (`frontend/vitest.config.ts`).
- Test setup starts the shared MSW server once per run and makes fake timers opt-in; unhandled requests warn by default, and timers are only restored when explicitly enabled (`frontend/src/test-setup.ts`).
- Auth store and validation tests now rely on MSW auth route handlers with factory-backed user fixtures, and handler utilities (`composeHandlers`, `createAuthRouteHandlers`) support per-test overrides (`frontend/src/test/msw/handlers/*`, `frontend/src/stores/__tests__/auth/*`).
- Chat attachments API tests now use MSW-backed upload/download handlers instead of global fetch mocks, covering single/batch uploads, errors, and auth header propagation (`frontend/src/app/api/chat/attachments/__tests__/route.test.ts`, `frontend/src/test/msw/handlers/attachments.ts`).
- Attachments files API test now asserts auth forwarding via MSW handler rather than fetch spies, aligning with centralized handler library (`frontend/src/app/api/attachments/files/__tests__/route.test.ts`).
- Calendar integration now uses absolute API base URLs and MSW handlers for Supabase and Google Calendar endpoints, improving Node test stability (`frontend/src/lib/calendar/calendar-integration.ts`, `frontend/src/lib/calendar/__tests__/calendar-integration.test.ts`).
- Accommodations end-to-end integration mocks Amadeus/Google Places/Stripe via MSW and in-memory clients, removing fetch spies and stabilizing booking flow assertions (`frontend/src/domain/accommodations/__tests__/accommodations.integration.test.ts`).
- State Department advisory provider tests now rely on MSW feed stubs instead of manual fetch mocks, covering cache, error, and timeout paths deterministically (`frontend/src/ai/tools/server/__tests__/travel-advisory-state-department.test.ts`).
- Added calendar event factory for reuse in integration tests and schema-validated fixtures (`frontend/src/test/factories.ts`, `frontend/src/lib/calendar/__tests__/calendar-integration.test.ts`).

- Centralized validation schemas for stores

### Fixed

- Realtime reconnection test now asserts `unsubscribe` is invoked before resubscribe, covering the full reconnection flow.
- Activities search comparison modal now closes correctly when the selection drops to one item and auto-opens only after an item is added.
- Memory context now preserves Supabase turn `created_at` and `id` through the Zod schema, Supabase adapter, `/api/memory/search` response, and AI memory search tool instead of synthesizing timestamps/UUIDs.
- Security dashboard again exposes terminate controls for non-current sessions and formats events, sessions, and last-login timestamps in the viewer’s locale via a client helper.
- Added missing route rate-limit entries for `security:events` and `security:metrics` to align with the security APIs’ guardrails.
- Chat non-stream handler now relies on `persistMemoryTurn` internal handling instead of double-logging persistence errors (`frontend/src/app/api/chat/_handler.ts`).
- Removed unreachable trip null guard after Supabase `.single()` when creating itinerary items, simplifying error handling (`frontend/src/app/api/itineraries/route.ts`).
- ICS import errors once again return the raw parse message in `details` (no nested `{ details }` wrapper) when validation fails (`frontend/src/app/api/calendar/ics/import/route.ts`).
- Restored chat RLS so trip collaborators can read shared sessions and assistant/system messages remain visible by scoping SELECT to session access instead of message authorship (`supabase/migrations/20251122000000_base_schema.sql`).
- Supabase base migration now skips stub vault creation when `supabase_vault` is installed and disambiguates `agent_config_upsert`/`user_has_trip_access` parameters so `npx supabase migration up` and `npx supabase db lint` succeed locally (`supabase/migrations/20251122000000_base_schema.sql`).
- **Accommodation booking**: `bookAccommodation` now uses the real amount and currency from check-availability input, and returns the same `bookingId` that is stored in Supabase.
- **Upcoming flights pricing**: `UpcomingFlights` renders prices using the flight currency instead of always prefixing USD.
- **Vitest stability**: Frontend Vitest config now clamps CI workers and adds a sharded `test:ci` script that runs the full suite in smaller batches to avoid jsdom/V8 heap pressure.
- **Client-side OTEL export wiring**: `frontend/src/lib/telemetry/client.ts` now attaches a `BatchSpanProcessor` to `WebTracerProvider` via `addSpanProcessor` before `register()`, ensuring browser spans are exported instead of being dropped; telemetry tests updated in `frontend/src/lib/telemetry/__tests__/client.test.ts` and `frontend/src/lib/telemetry/__tests__/client-errors.test.ts`.
- **Agent tool error codes**: Updated rate limiting error codes from `webSearchRateLimited` to `toolRateLimited` for non-search tools (POI lookup, combine search results, travel advisory, crawl, weather, geocode, distance matrix) to match semantic purpose.
- **Agent cache configuration**: Re-enabled `hashInput: true` on all agent tool cache guardrails so Redis keys include per-request hashes, preventing stale cross-user responses.

- Security session handlers now await telemetry spans and select full auth session columns to keep Supabase responses typed and traceable.
- Supabase SSR factory and server tests now stub `@supabase/ssr.createServerClient`, `getServerEnv()`, and `getClientEnv()` explicitly, so Zod environment validation and cookie adapters are tested deterministically in `frontend/src/lib/supabase/__tests__/factory.spec.ts` and `frontend/src/lib/supabase/__tests__/server.test.ts` without relying on process environment side effects.
- Supabase Realtime hooks now provide stable runtime behaviour: `useTripRealtime` memoizes its error instance to avoid unnecessary error object churn; `useWebSocketChat` now delegates channel subscription to the shared `useRealtimeChannel` helper and uses Supabase's built-in reconnection, removing duplicated backoff logic.
- Agent status WebSocket reconnect backoff in `frontend/src/hooks/use-agent-status-websocket.ts` now increments attempts via a state updater and derives delays from the updated value, so retry intervals grow exponentially and reset only on successful subscription instead of remaining fixed.
- Chat store realtime lifecycle is guarded by tests: `disconnectRealtime` in `frontend/src/stores/chat-store.ts` is covered by `frontend/src/stores/__tests__/chat-store-realtime.test.ts` to ensure connection status, pending messages, channel reference, and typing state are reset consistently when the UI tears down the realtime connection.
- Login form now sanitizes `next`/`from` redirects to same-origin paths only, blocking protocol-relative and off-origin redirects (`frontend/src/components/auth/login-form.tsx`).
- `POST /api/auth/login` returns 400 for malformed JSON bodies instead of 500, improving client feedback and telemetry accuracy (`frontend/src/app/api/auth/login/route.ts`).
- Client OTEL fetch instrumentation narrows `propagateTraceHeaderCorsUrls` to the exact origin to prevent trace header leakage to attacker-controlled hosts (`frontend/src/lib/telemetry/client.ts`).
- ApiClient base URL normalization no longer duplicates `/api` when a relative base is supplied and has a regression test to lock the behavior (`frontend/src/lib/api/api-client.ts`, `frontend/src/lib/api/__tests__/api-client.test.ts`).
- Fixed type-check/lint regressions in accommodations and calendar tests/factories (mocked caching module typing, calendar event factories returning Dates, MSW handler naming) and cleaned calendar export test to guard request parsing.

## [1.0.0] - 2025-11-14

### [1.0.0] Added

- APP_BASE_URL server setting (env schema + `.env.example`) and Stripe payment return URL now resolved via `getServerEnvVarWithFallback`, so server-only flows no longer pull from client-prefixed env vars (frontend/src/lib/env/schema.ts, frontend/.env.example, frontend/src/lib/payments/stripe-client.ts).
- AI demo telemetry endpoint (`frontend/src/app/api/telemetry/ai-demo/route.ts`) plus client hooks in `frontend/src/app/ai-demo/page.tsx` emit structured success/error events instead of console logging.
- Supabase Database Webhooks via `pg_net`/`pgcrypto` with HMAC header; initial HTTP trigger for `trip_collaborators` posting to Vercel (`supabase/migrations/20251113031500_pg_net_webhooks_triggers.sql`).
- Next.js webhook handlers (Node runtime, dynamic): `/api/hooks/trips`, `/api/hooks/files`, `/api/hooks/cache`, `/api/embeddings` with request HMAC verification and Redis idempotency.
- Shared utilities:
  - `frontend/src/lib/security/webhook.ts` (HMAC compute/verify with timing‑safe compare)
  - `frontend/src/lib/idempotency/redis.ts` (Upstash `SET NX EX`)
  - `frontend/src/lib/webhooks/payload.ts` (parse/verify helper + stable event key)
- Vercel functions config with Node 20.x, 60s max duration, and regional pinning (`vercel.json`).
- Flight and accommodation search result cards: `FlightOfferCard` and `StayCard` components in `frontend/src/components/ai-elements/` rendering structured results with itineraries, pricing, and source citations.
- Chat message JSON parsing: `ChatMessageItem` detects and validates `flight.v1` and `stay.v1` schema JSON in text parts, rendering cards instead of raw text.
- Agent routing in chat transport: `DefaultChatTransport.prepareSendMessagesRequest` routes messages with `metadata.agent` to `/api/agents/flights` or `/api/agents/accommodations`; falls back to `/api/chat/stream` for general chat.
- Quick Actions metadata: Flight and accommodation quick actions send Zod-shaped requests via message metadata (`metadata.agent` and `metadata.request`).
- Gateway fallback in provider registry: `resolveProvider` falls back to Vercel AI Gateway when no BYOK keys found; BYOK checked first, Gateway used as default for non-BYOK users.
- Web search batch tool (multi‑query): `frontend/src/lib/tools/web-search-batch.ts` with bounded concurrency, per‑item results, and optional top‑level RL.
- OpenTelemetry spans for web search tools using `withTelemetrySpan`:
  - `tool.web_search` (attributes: categoriesCount, sourcesCount, hasLocation, hasTbs, fresh, limit)
  - `tool.web_search_batch` (attributes: count, fresh)
- Web search tests:
  - Telemetry and rate‑limit wiring for single search: `frontend/src/lib/tools/__tests__/web-search.test.ts`
  - Batch behavior and per‑query error handling: `frontend/src/lib/tools/__tests__/web-search-batch.test.ts`
- Types for web search params/results: `frontend/src/types/web-search.ts`.
- Strict structured output validation for web search tools: Zod schemas (`WEB_SEARCH_OUTPUT_SCHEMA`, `WEB_SEARCH_BATCH_OUTPUT_SCHEMA`) in `frontend/src/types/web-search.ts`; outputs validated at execution boundaries with `.strict()`.
- Chat UI shows published time when available on search cards: `frontend/src/app/chat/page.tsx`.
- Request-scoped Upstash limiter builder shared by BYOK routes: `frontend/src/app/api/keys/_rate-limiter.ts` plus span attribute helper `frontend/src/app/api/keys/_telemetry.ts`.
- Minimal OpenTelemetry span utility with attribute redaction and unit tests: `frontend/src/lib/telemetry/span.ts` and `frontend/src/lib/telemetry/__tests__/span.test.ts`.
- Dependency: `@opentelemetry/api@1.9.0` (frontend) powering BYOK telemetry spans.
- Route-helper coverage proving rate-limit identifiers always fall back to `"unknown"`: `frontend/src/lib/next/__tests__/route-helpers.test.ts`.
- Shared test store factories for Zustand mocks:
  - `frontend/src/test/factories/stores.ts` (`createMockChatState`, `createMockAgentStatusState`).
- Timer test helper for deterministic, immediate execution:
  - `frontend/src/test/timers.ts` (`shortCircuitSetTimeout`).
- Secure random ID utility with fallbacks: `frontend/src/lib/security/random.ts` exporting `secureUUID()`, `secureId()`, and `nowIso()`; Vitest coverage in `frontend/src/lib/security/random.test.ts`.
- Dependency-injected handlers for App Router APIs:
  - Chat stream: `frontend/src/app/api/chat/stream/_handler.ts`
  - Chat (non-stream): `frontend/src/app/api/chat/_handler.ts`
  - Keys (BYOK): `frontend/src/app/api/keys/_handlers.ts`
  - Sessions/messages: `frontend/src/app/api/chat/sessions/_handlers.ts`
- Attachment utilities and validation:
  - `frontend/src/app/api/_helpers/attachments.ts`
- Deterministic Vitest suites for handlers and adapter smokes:
  - Chat stream handler and route smokes under `frontend/src/app/api/chat/stream/__tests__/`
  - Chat non-stream handler and route smokes under `frontend/src/app/api/chat/__tests__/`
  - Keys and sessions handler tests under `frontend/src/app/api/keys/__tests__/` and `frontend/src/app/api/chat/sessions/__tests__/`
- Frontend agent guidelines for DI handlers, thin adapters, lazy RL, and testing:
  - `frontend/AGENTS.md`
- ADR documenting DI handlers + thin adapters testing strategy:
  - `docs/adrs/adr-0029-di-route-handlers-and-testing.md`
  - `docs/adrs/adr-0031-nextjs-chat-api-ai-sdk-v6.md` (Next.js chat API canonical)
  - `docs/specs/spec-chat-api-sse-nonstream.md` (contracts and errors)
- Provider registry and resolution (server-only) returning AI SDK v6 `LanguageModel`:
  - `frontend/src/ai/models/registry.ts` (`resolveProvider(userId, modelHint?)`)
  - `frontend/src/lib/providers/types.ts`
  - Temporary shim that re-exported the registry has been removed; use `frontend/src/ai/models/registry.ts` directly
- OpenRouter provider: switch to `@ai-sdk/openai` with `baseURL: https://openrouter.ai/api/v1` (remove `@openrouter/ai-sdk-provider`); attribution headers remain removed
- Vitest unit tests for registry precedence and attribution
  - `frontend/src/lib/providers/__tests__/registry.test.ts`
- Architecture docs: ADR and Spec for provider order, attribution, and SSR boundaries
  - `docs/adrs/2025-11-01-provider-registry.md`, `docs/specs/provider-registry.md`
- Dependency: `@ai-sdk/anthropic@3.0.0-beta.47`
- AI Elements Response and Sources components with focused tests:
  - `frontend/src/components/ai-elements/response.tsx`
  - `frontend/src/components/ai-elements/sources.tsx`
  - Tests in `frontend/src/components/ai-elements/__tests__/`
- Streamdown CSS source for Response rendering:
  - `frontend/src/app/globals.css`
- Architecture records and specs:
  - `docs/adrs/adr-0035-react-compiler-and-component-declarations.md`
  - `docs/adrs/adr-0036-ai-elements-response-and-sources.md`
  - `docs/adrs/adr-0037-reasoning-tool-codeblock-phased-adoption.md`
  - `docs/specs/0015-spec-ai-elements-response-sources.md`
  - `docs/specs/0016-spec-react-compiler-enable.md`
- Testing support stubs and helpers:
  - Rehype harden test stub to isolate ESM/CJS packaging differences: `frontend/src/test/mocks/rehype-harden.ts` (aliased in Vitest config)
- Calendar integration tests and utilities:
  - Shared test helpers: `frontend/src/app/api/calendar/__tests__/test-helpers.ts` with hoisted mocks (`vi.hoisted()`), `setupCalendarMocks()` factory, and `buildMockRequest()` helper for consistent route testing.
  - Integration test coverage: 74 tests across 7 files covering unauthorized (401), rate limits (429), Google API errors, empty arrays, partial updates, multiple events, and timezone handling.
  - Schema test edge cases: invalid date formats, missing required fields, length validation (summary ≤1024, description ≤8192), email format validation, `timeMax > timeMin` validation for free/busy requests.
  - Trip export tests: empty destinations, missing dates/activities, partial trip data, metadata structure validation.
  - E2E test optimizations: parallel assertions via `Promise.all()`, optimized wait strategies (`domcontentloaded`), explicit timeouts for CI stability.
- Test documentation: `frontend/src/app/api/calendar/__tests__/README.md` with usage examples and best practices.
- Travel Planning tools (AI SDK v6, TypeScript):
  - Server-only tools: `createTravelPlan`, `updateTravelPlan`, `combineSearchResults`, `saveTravelPlan`, `deleteTravelPlan` in `frontend/src/ai/tools/server/planning.ts`.
  - Zod schema for persisted plans: `frontend/src/ai/tools/server/planning.schema.ts` with camelCase fields.
  - Upstash Redis persistence: keys `travel_plan:{planId}` with 7d default TTL, 30d for finalized plans.
  - User injection: `wrapToolsWithUserId()` in `frontend/src/ai/tools/server/injection.ts` for authenticated tool calls.
  - Rate limits: create 20/day per user; update 60/min per plan.
  - Tests: `frontend/src/ai/tools/server/__tests__/planning.test.ts` covers schema validation, Redis fallbacks, rate limits.
- Agent endpoints (P1-P4 complete):
  - `frontend/src/app/api/agents/flights/route.ts` (P1)
  - `frontend/src/app/api/agents/accommodations/route.ts` (P1)
  - `frontend/src/app/api/agents/budget/route.ts` (P2)
  - `frontend/src/app/api/agents/memory/route.ts` (P2)
  - `frontend/src/app/api/agents/destinations/route.ts` (P2)
  - `frontend/src/app/api/agents/itineraries/route.ts` (P2)
  - `frontend/src/app/api/agents/router/route.ts` (P3)
- Agent orchestrators (AI SDK v6 `streamText` + guardrails):
  - `frontend/src/lib/agents/flight-agent.ts`, `accommodation-agent.ts`, `budget-agent.ts`, `memory-agent.ts`, `destination-agent.ts`, `itinerary-agent.ts`, `router-agent.ts`
- Centralized rate limit configuration:
  - `frontend/src/lib/ratelimit/config.ts` with `buildRateLimit(workflow, identifier)` factory replacing per-workflow builders
  - All agents use unified rate limit config with consistent 1-minute windows
- Provider tools:
  - `frontend/src/ai/tools/server/google-places.ts` for POI lookups using Google Places API (New). Uses Google Maps Geocoding API for destination-based lookups with 30-day max cached results per policy.
  - `frontend/src/ai/tools/server/travel-advisory.ts` for travel advisories and safety scores based on the U.S. State Department Travel Advisories API with cached responses.
- UI components for agent results:
  - `BudgetChart` for budget planning visualization
  - `DestinationCard` for destination research results
  - `ItineraryTimeline` for itinerary planning display
- Error recovery: `frontend/src/lib/agents/error-recovery.ts` with standardized error mapping and streaming error handlers
- Tests for agents and tools:
  - Route validation and happy-path tests under `frontend/src/app/api/agents/**/__tests__/`
  - Rate limit builder tests: `frontend/src/lib/ratelimit/__tests__/builders.test.ts`
  - Google Places and Travel Advisory tool tests with input validation
  - Guardrail telemetry tests: `frontend/src/lib/agents/__tests__/runtime.test.ts`
  - E2E Playwright tests: `frontend/e2e/agents-budget-memory.spec.ts`
- Operator runbook: `docs/operations/agent-frontend.md` updated with all endpoints and env vars

- Trip collaborator notifications via Supabase Database Webhooks, Upstash QStash, and Resend:
  - QStash-managed worker route `/api/jobs/notify-collaborators` verifies `Upstash-Signature`, validates jobs with Zod, and calls the notification adapter.
  - Notification adapter `frontend/src/lib/notifications/collaborators.ts` sends Resend emails and optional downstream webhooks with Redis-backed idempotency.
  - Webhook payload normalization helper `frontend/src/lib/webhooks/payload.ts` parses raw Supabase payloads, verifies HMAC (`HMAC_SECRET`), and builds stable event keys.
  - Vitest coverage for `/api/jobs/notify-collaborators` covering missing keys, signature failures, schema validation, duplicate suppression, and successful notification runs.
- Embeddings API route `/api/embeddings` now uses AI SDK v6 `embed` with OpenAI `text-embedding-3-small`, returning 1536‑dimensional embeddings with usage metadata.
- Zod schemas for webhook payloads and notification jobs in `frontend/src/lib/schemas/webhooks.ts`.
- ADR-0041 documenting QStash + Resend notification pipeline and SPEC-0025 defining trip collaborator notification behavior.

### [1.0.0] Changed

- Agent routes for budget, destination, itinerary, memory, and router flows now call `errorResponse`, `enforceRouteRateLimit`, and `withRequestSpan` before invoking their orchestrators to keep throttling and telemetry consistent.
- Budget/destination/itinerary orchestrators now build every tool via `buildGuardedTool` with concrete Zod schemas (web search batch, POI lookup, planning combine/save, travel advisory, weather, crawl) instead of bespoke `runWithGuardrails` blocks using `z.any`.
- Chat page routing: Messages with agent metadata route to specialized endpoints; JSON parsing extracts structured results from markdown code blocks or plain text.
- Provider registry resolution: Checks BYOK keys first (direct provider access), then falls back to Gateway (default path for non-BYOK users).
- Web search tool (`frontend/src/lib/tools/web-search.ts`):
  - Uses `fetchWithRetry` with bounded timeouts; direct Firecrawl v2 `/search` POST.
  - Adds input guards (query ≤256, location ≤120), accepts custom category strings.
  - Adds TTL heuristics (realtime/news/daily/semi‑static) for Redis cache; keeps canonical cache keys (flattened `scrapeOptions`).
  - Returns `{ fromCache, tookMs }` metadata; integrates Upstash RL (20/min) keyed by `userId`.
  - Pass‑through support for undocumented `region`/`freshness` only when provided.
  - Enforces strict structured outputs via Zod schemas; all code paths (cache hits, API responses, error fallbacks) return validated shapes matching `WEB_SEARCH_OUTPUT_SCHEMA`.
  - Normalizes Firecrawl responses to strip extra fields (content, score, source) before validation; stores normalized data in cache for consistency.
- Web search batch tool (`frontend/src/lib/tools/web-search-batch.ts`): Enforces strict structured outputs via `WEB_SEARCH_BATCH_OUTPUT_SCHEMA`; per-query success/error shapes validated at execution boundaries. Normalizes results from both primary execution and HTTP fallback paths.
- Accommodation tools (`frontend/src/ai/tools/server/accommodations.ts`): Enforce strict structured outputs via Zod schemas (`ACCOMMODATION_SEARCH_OUTPUT_SCHEMA`, `ACCOMMODATION_DETAILS_OUTPUT_SCHEMA`, `ACCOMMODATION_BOOKING_OUTPUT_SCHEMA`); all code paths return validated shapes. Session context injection via `wrapToolsWithUserId` for booking approval flow. Centralized error taxonomy (`frontend/src/ai/tools/server/errors.ts`) with `TOOL_ERROR_CODES` and `createToolError` helper adopted across accommodation tools.
- Chat UI renders web search results as cards with title/snippet/URL, citations via AI Elements `Sources`, and displays `fromCache` + `tookMs`.
- Env: `.env.example` simplified — require only `FIRECRAWL_API_KEY`; `FIRECRAWL_BASE_URL` optional for self‑hosted Firecrawl.
- Env: frontend `.env.example` extended with notification and webhook variables (`RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_FROM_NAME`, `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`, `COLLAB_WEBHOOK_URL`, `HMAC_SECRET`) and wired through `frontend/src/lib/env/schema.ts`.
- Notification behavior for `trip_collaborators` webhooks now flows through `/api/hooks/trips` → QStash queue → `/api/jobs/notify-collaborators`, replacing any legacy in-route side effects.
- Notification pipeline hardening:
  - `/api/jobs/notify-collaborators` now fails closed when QStash signing keys are missing and always verifies `Upstash-Signature` before processing jobs.
  - `/api/hooks/trips` fallback execution runs inside its own telemetry span to retain error visibility without touching closed parent spans.
  - SPEC-0021, the operator guide, and `.env.example` now describe the cache tag bump strategy and the requirement to configure QStash signing keys before accepting jobs.
- BYOK POST/DELETE adapters (`frontend/src/app/api/keys/route.ts`, `frontend/src/app/api/keys/[service]/route.ts`) now build rate limiters per request, derive identifiers per user/IP, and wrap Supabase RPC calls in telemetry spans carrying rate-limit attributes and sanitized key metadata; route tests updated to stub the new factory and span helper.
- Same BYOK routes now export `dynamic = "force-dynamic"`/`revalidate = 0` and document the no-cache rationale so user-specific secrets never reuse stale responses.
- Service normalization and rate-limit identifier behavior are documented/tested (see `frontend/src/app/api/keys/_handlers.ts`, route tests, and `frontend/src/lib/next/route-helpers.ts`), closing reviewer feedback.
- Telemetry: planning tool executions wrapped in OpenTelemetry spans; rate-limit events recorded via OTEL with consistent attributes.
- Frontend test utilities moved out of `*.test.*` globs to avoid accidental collection; imports updated:
  - `frontend/src/test/test-utils.test.tsx` → `frontend/src/test/test-utils.tsx` and all references switched to `@/test/test-utils`.
- AI stream route integration tests optimized:
  - Stubbed expensive token utilities (`clampMaxTokens`, `countPromptTokens`) in `frontend/src/app/api/ai/stream/__tests__/route.integration.test.ts`.
  - Reduced long prompt payload from 10k chars to a compact representative sample.
- Chat layout component made injectible and test-friendly:
  - Removed hard-coded sessions; added optional `sessions` prop and semantic attributes (`data-testid="chat-sidebar"`, `data-collapsed`) in `frontend/src/components/layouts/chat-layout.tsx`.
  - Tests use partial module mocks and `userEvent`; standardized timer teardown (`runOnlyPendingTimers` → `clearAllTimers` → `useRealTimers`).
- Account settings tests stabilized without fake timers:
  - Replaced suite-level fake timers with local `setTimeout` short-circuit stubs where needed and simplified assertions in `frontend/src/components/features/profile/__tests__/account-settings-section.test.tsx`.
- Itinerary builder suite condensed to essential scenarios and de-timed:
  - Pruned heavy/duplicated cases; retained empty state, minimal destination info, add-destination happy path, numeric input, and labels in `frontend/src/components/features/trips/__tests__/itinerary-builder.test.tsx`.
- Test performance documentation updated with reproducible commands and “After” metrics:
  - `frontend/docs/testing/vitest-performance.md` (AI stream ≈12.6ms; Account settings ≈1.6s; Itinerary builder ≈1.5s).
- Operational alerting improvements:
  - Added `frontend/src/lib/telemetry/tracer.ts` for a single OTEL tracer name and `frontend/src/lib/telemetry/alerts.ts` for `[operational-alert]` JSON logs, with Vitest coverage for tracer, alerts, Redis warnings, and webhook payload failures.
  - Redis cache/idempotency helpers now emit alerts alongside `redis.unavailable` spans, and `parseAndVerify` logs `webhook.verification_failed` with precise reasons; operator docs and the storage deployment summary explain how to wire log drains for both events.
- Deployment workflow enforces webhook secret parity: `.github/workflows/deploy.yml` installs `psql`, runs `scripts/operators/verify_webhook_secret.sh`, and requires `PRIMARY_DATABASE_URL` (falling back to `DATABASE_URL`) plus `HMAC_SECRET` secrets; docs highlight the CI guard and primary-DB requirement.
- Observability guide documents `[operational-alert]` usage and current events (`redis.unavailable`, `webhook.verification_failed`); developer README links to the guide for future telemetry changes.
- `.github/ci-config.yml` lists `PRIMARY_DATABASE_URL` and `HMAC_SECRET` under `secrets.deploy` so deploy requirements remain visible in config.
- Flights tool now prefers `DUFFEL_ACCESS_TOKEN` (fallback `DUFFEL_API_KEY`)
  - `frontend/src/lib/tools/flights.ts`
- Agent temperatures are hard-coded to `0.3` per agent (no env overrides)
  - `frontend/src/lib/agents/{flight-agent,accommodation-agent,budget-agent,memory-agent,destination-agent,itinerary-agent,router-agent}.ts`
- AgentWorkflow enum refactored from snake_case to camelCase for Google TS style compliance
  - Updated `frontend/src/schemas/agents.ts` enum values: `flightSearch`, `accommodationSearch`, `budgetPlanning`, `memoryUpdate`, `destinationResearch`, `itineraryPlanning`, `router`
  - All agent files, UI components, and tests updated to use camelCase workflow strings
- Rate limit configuration centralized and DRY optimized
  - Removed per-workflow builder files (`ratelimit/flight.ts`, `ratelimit/accommodation.ts`, `ratelimit/budget.ts`, `ratelimit/memory.ts`, `ratelimit/destinations.ts`, `ratelimit/itineraries.ts`)
  - Consolidated into `frontend/src/lib/ratelimit/config.ts` with `RATE_LIMIT_CONFIG` map and `buildRateLimit()` factory
- Legacy POI lookup tool removed and replaced with Google Places API integration
  - Deleted `frontend/src/lib/tools/opentripmap.ts` and test suite
  - All imports updated to use `frontend/src/lib/tools/google-places.ts` directly
  - Google Places tool implements Google Maps geocoding for destination strings: `geocodeDestinationWithGoogleMaps()` function with normalized cache keys (`googleplaces:geocode:{destination}`), 30-day max TTL per policy
- Environment variables added to `.env.example`:
  - `GOOGLE_MAPS_SERVER_API_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY`, `GEOSURE_API_KEY`, `AI_GATEWAY_API_KEY`, `AI_GATEWAY_URL`
  - `OPENWEATHERMAP_API_KEY`, `DUFFEL_API_KEY`, `ACCOM_SEARCH_URL`, `ACCOM_SEARCH_TOKEN`, `AIRBNB_MCP_URL`, `AIRBNB_MCP_API_KEY`
- Specs updated for full frontend cutover
  - `docs/specs/0019-spec-hybrid-destination-itinerary-agents.md`
  - `docs/specs/0020-spec-multi-agent-frontend-migration.md` (P2-P4 complete)
- Replaced insecure/random ID generation across frontend stores and error pages with `secureId/secureUUID` and normalized timestamps via `nowIso`.
- Removed server-side `Math.random` fallback for chat stream request IDs; use `secureUUID()` in `frontend/src/app/api/chat/stream/_handler.ts:1`.
- Stabilized skeleton components: removed `Math.random` usage in `travel-skeletons.tsx` and `loading-skeletons.tsx` to ensure deterministic rendering.
- Adopted PascalCase names for page components in App Router to align with ADR-0035.
- Chat page now consumes AI SDK v6 `useChat` + `DefaultChatTransport`, removing the bespoke SSE parser and wiring Supabase user IDs into the payload (`frontend/src/app/chat/page.tsx`).
- Chat page renders message `text` via AI Elements `Response` and shows `Sources` when `source-url` parts are present (`frontend/src/app/chat/page.tsx`).
- Enabled React Compiler in Next.js configuration (`frontend/next.config.ts`).
- Chat stream adapter now delegates to DI handler and builds the Upstash rate limiter lazily:
  - `frontend/src/app/api/chat/stream/route.ts`
- Chat non-stream route added with DI handler, usage mapping, image-only validation, and RL parity (40/min):
  - `frontend/src/app/api/chat/route.ts`, `frontend/src/app/api/chat/_handler.ts`
- Stream emits `resumableId` in start metadata; client `useChat` wired with `resume: true` and reconnect transport; a brief "Reconnected" toast is shown after resume.
- OpenAPI snapshot updated to reflect removal of Python chat endpoints.
- Keys and sessions adapters delegate to their DI handlers:
  - `frontend/src/app/api/keys/route.ts`
  - `frontend/src/app/api/chat/sessions/route.ts`
  - `frontend/src/app/api/chat/sessions/[id]/route.ts`
  - `frontend/src/app/api/chat/sessions/[id]/messages/route.ts`
- Vitest defaults tuned for stability and timeouts:
  - `frontend/vitest.config.ts` (unstubEnvs, threads, single worker)
  - `frontend/package.json` test scripts include short timeouts
- **Tooling:** Consolidated lint/format to Biome (`biome check`), removed ESLint/Prettier/lint-staged.
- Frontend testing configuration and performance:
  - Vitest pool selection: use `vmForks` in CI and `vmThreads` locally to reduce worker hangs on large suites (`frontend/vitest.config.ts`).
  - Enable CSS transformation for web dependencies (`deps.web.transformCss: true`) to fix “Unknown file extension .css” in node_modules.
  - Inline/ssr-handle `rehype-harden` to avoid ESM-in-CJS packaging errors during tests (`test.server.deps.inline`, `ssr.noExternal`, and alias).
  - Aliased `rehype-harden` to a minimal no-op transformer for tests.
  - Added global Web Streams polyfills in test setup using `node:stream/web` with correct lib.dom-compatible typing.
  - Mocked `next/image` to a basic `<img>` in tests to eliminate jsdom/ESM overhead and speed up UI tests.
  - Avoid redefining `window.location`; rely on JSDOM defaults to prevent non-configurable property errors.
  - Hoisted module mocks with `vi.hoisted` where needed to satisfy Vitest hoisting semantics.

#### [1.0.0] Database / RAG

- Supabase RAG schema has been finalized on a dedicated `public.accommodation_embeddings` table with 1,536‑dimension `pgvector` embeddings, IVFFlat index, and a `match_accommodation_embeddings` RPC for semantic search. This removes the previous conflict between trip-owned `accommodations` rows and RAG vectors and ensures clean greenfield migrations (`supabase/migrations/20251113024300_create_accommodations_rag.sql`, `supabase/migrations/20251114120000_update_accommodations_embeddings_1536.sql`).
- Embeddings persistence now writes exclusively to `public.accommodation_embeddings` via the `/api/embeddings` route using the Supabase admin client, and the accommodations search tool calls the renamed `match_accommodation_embeddings` RPC when a `semanticQuery` is provided (`frontend/src/app/api/embeddings/route.ts`, `frontend/src/lib/tools/accommodations.ts`).
- Supabase types were updated to include a strongly typed `accommodation_embeddings` table and `AccommodationEmbedding` helper type so all embedding reads/writes are fully typed (`frontend/src/lib/supabase/database.types.ts`).
- Added a canonical schema loader `supabase/schema.sql` that applies all migrations in the correct order, plus a Supabase bootstrap guide documenting single-command setup for new projects (`docs/ops/supabase-bootstrap.md`).

### [1.0.0] Fixed

- `/api/geocode` returns `errorResponse` payloads for validation failures and Google Maps upstream errors, replacing brittle custom JSON branches.
- `.env` docs, Docker compose, and tests now point to a single `OPENWEATHER_API_KEY`, removing the duplicate `OPENWEATHERMAP_API_KEY` guidance that caused misconfiguration.
- Token budget utilities release WASM tokenizer resources without `any` casts (`frontend/src/lib/tokens/budget.ts`).
- Google Places POI lookup now supports destination-only queries via Google Maps geocoding: uses `geocodeDestinationWithGoogleMaps()` implementation with Google Maps Geocoding API, added geocoding result caching (30-day max TTL per policy), normalized cache keys for consistent lookups (`frontend/src/lib/tools/google-places.ts`).
- Date formatting is now timezone-agnostic for `YYYY-MM-DD` inputs to avoid CI/system TZ drift; ISO datetimes format in UTC (`frontend/src/lib/schema-adapters.ts`, tests updated in `frontend/src/lib/__tests__/schema-adapters.test.ts`).
- Calendar schema validation: `freeBusyRequestSchema` now validates `timeMax > timeMin` using Zod `.refine()` to reject invalid time ranges (`frontend/src/schemas/calendar.ts`).
- Stabilized long‑prompt AI stream test by bounding tokenizer work and retaining accuracy:
  - Introduced a safe character threshold for WASM tokenization with heuristic fallback; small/normal inputs still use `js-tiktoken` and tests validate encodings (`frontend/src/lib/tokens/budget.ts`, `frontend/src/lib/tokens/__tests__/budget.test.ts`).
  - Ensures `handles very long prompt content` completes within per‑suite timeout.
- CI non‑terminating runs addressed via Vitest config hardening:
  - Use `vmForks` in CI, low worker count, explicit bail, and deterministic setup to prevent lingering handles (`frontend/vitest.config.ts`).
  - Web Streams and Next/Image mocks consolidated in `frontend/src/test-setup.ts` to avoid environment leaks; console/env proxies reset after each test.
- Resolved hanging API tests by:
  - Injecting a finite AI stream stub in handler tests (no open handles)
  - Building Upstash rate limiters lazily (no module‑scope side effects)
  - Guarding JSDOM‑specific globals in `frontend/src/test-setup.ts`
  - Using `vi.resetModules()` and env stubs before importing route modules
- Centralized BYOK provider selection; preference order: openai → openrouter → anthropic → xai
- OpenRouter and xAI wired via OpenAI-compatible client with per-user BYOK and required base URLs
- Registry is SSR-only (`server-only`), never returns or logs secret material
- Session message listing and creation stay scoped to the authenticated user (`frontend/src/app/api/chat/sessions/_handlers.ts`).
- Frontend test stability and failures:
  - Resolved CSS import failures by enabling CSS transforms for web deps and adjusting the pool to VM runners.
  - Fixed ESM/CJS mismatch from `rehype-harden` by inlining and aliasing to a stub in tests.
  - Eliminated hoist-related `vi.mock` errors by moving test-local mock components into `vi.hoisted` blocks.
  - Removed brittle `window.location` property redefinitions (location/reload/href) in tests; replaced with behavior assertions that don't require redefining non-configurable globals.
  - Added Web Streams polyfills to fix `TransformStream is not defined` in chat UI tests (AI SDK/eventsource-parser).
  - Mocked `@/components/ai-elements/response` in chat page tests to avoid rehype/Streamdown transitive ESM during unit tests.
  - Shortened and stabilized slow suites (e.g., search/accommodation-card) by mocking `next/image` and increasing a single long-running test timeout where appropriate.
  - Adjusted auth-store time comparison to avoid strict-equality flakiness on timestamp rollover.
- Calendar test performance: Shared mocks via `vi.hoisted()` reduce setup overhead; tests run in parallel (Vitest threads pool); execution time ~1.1s for 74 tests across 7 files; coverage targets met (90% lines/statements/functions, 85% branches).
- Planning data model is now camelCase and TypeScript-first (no Python compatibility retained):
  - Persisted fields include `planId`, `userId`, `title`, `destinations`, `startDate`, `endDate`, `travelers`, `budget`, `preferences`, `createdAt`, `updatedAt`, `status`, `finalizedAt`, `components`.
  - `updateTravelPlan` validates updates via Zod partial schema; unknown/invalid fields are rejected.
  - `combineSearchResults` derives nights from `startDate`/`endDate` (default 3 when absent).
  - Non‑stream chat handler now includes tool registry and injects `userId` like streaming handler.
  - Added rate limits: create 20/day per user; update 60/min per plan (TTL set only when counter=1).
  - Markdown summary uses camelCase only; legacy snake_case fallbacks removed.
  - Stream and non‑stream handlers refactored to use `wrapToolsWithUserId()` and planning tool allowlist.

### [1.0.0] Removed

- Decommissioned Supabase Edge Functions (Deno) and tests under `supabase/functions/*` and `supabase/edge-functions/*`.
- Removed Supabase CLI function deploy/logs targets and Deno lockfile helpers from `Makefile`.
- Deleted legacy triggers file superseded by Database Webhooks.
- Feature flag/wave gating for agents
- Deleted `docs/operations/agent-waves.md`
  - Removed `AGENT_WAVE_*` references from tests
- Per-agent temperature env variables
  - Deleted `frontend/src/lib/settings/agent-config.ts`
  - Removed `AGENT_TEMP_*` usage in orchestrators
- Legacy Python web search module and references:
  - Deleted `tripsage/tools/web_tools.py` (CachedWebSearchTool, batch_web_search, decorators).
  - Removed import in `tripsage_core/services/business/activity_service.py`.
- Hard-coded sample sessions from chat layout; callers/tests inject sessions as needed (`frontend/src/components/layouts/chat-layout.tsx`).
- Redundant/high-cost UI cases from Itinerary builder tests (drag & drop visuals, delete flow, extra icon and cancel cases) to reduce runtime (`frontend/src/components/features/trips/__tests__/itinerary-builder.test.tsx`).
- Obsolete test wrapper file `frontend/src/test/test-utils.test.tsx` (replaced by `frontend/src/test/test-utils.tsx`).
- Python provider wrappers and tests removed (see Breaking Changes)
- FastAPI chat router and schemas removed; chat moved to Next.js AI SDK v6
  - Deleted: `tripsage/api/routers/chat.py`, `tripsage/api/schemas/chat.py`
  - Pruned router import list: `tripsage/api/routers/__init__.py`
- Removed ChatAgent and chat service wiring: `tripsage/agents/chat.py`, ChatAgent initialization in `tripsage/api/main.py`, chat service from `tripsage/app_state.py`, ChatService from `tripsage_core/services/business/chat_service.py`
- Deleted tests and fixtures tied to Python chat: `tests/integration/api/test_chat_streaming.py`, `tests/e2e/test_agent_config_flow.py`, `tests/fixtures/http.py`, and `tests/unit/agents/test_create_agent.py`
- Core chat models and orchestration removed from Python:
  - Deleted: `tripsage_core/models/db/chat.py`, `tripsage_core/models/schemas_common/chat.py`, `tripsage_core/services/business/chat_orchestration.py`, `tests/factories/chat.py`
  - Updated exports to remove chat DB/schemas: `tripsage_core/models/db/__init__.py`, `tripsage_core/models/schemas_common/__init__.py`, `tripsage_core/models/__init__.py`

### [1.0.0] Security

- Pinned `search_path` on SECURITY DEFINER functions and restricted EXECUTE/SELECT grants; enabled strict RLS on `webhook_logs` (service role only).
- Prevented `X-Signature-HMAC: null` headers from DB when secret is unset; server rejects invalid/missing signatures.
- Fixed timing-safe comparison bug and guarded hex parsing in HMAC verification to avoid DoS on malformed headers.
- Provider keys are fetched via server-side Supabase RPCs only; no client exposure
- OpenRouter attribution headers are non-sensitive and attached only when set

### [1.0.0] Breaking Changes

- Removed legacy Python LLM provider modules and corresponding tests:
  - `tripsage_core/services/external_apis/llm_providers.py`
  - `tripsage_core/services/external_apis/providers/{openai_adapter.py, openrouter_adapter.py, anthropic_adapter.py, xai_adapter.py, token_budget.py, interfaces.py}`
  - `tests/unit/external/{test_llm_providers.py, test_providers.py, test_token_budget.py}`
- No backwards compatibility shims retained; registry is the final implementation
- Removed Python chat API entirely in favor of Next.js routes using AI SDK v6; any direct callers to `/api/chat/*` must use `/app/api/chat/stream` (Next.js) instead

### [1.0.0] Refactor

- **[Core]:** Standardized all data fetching on TanStack Query, removing custom abstraction hooks (`useApiQuery`, `useSupabaseQuery`) to simplify server state management. All data fetching hooks now use `useQuery` and `useMutation` directly with the unified `apiClient` from `useAuthenticatedApi()`.
  - Removed custom `getSessionId` helper in favor of the shared utility in `src/lib/utils.ts`.
- **[Trips]:** Unified three separate trip data hooks into a single `useTrips` hook to manage all CRUD operations and real-time updates for the trip domain.
- **[API]:** Consolidated three separate API clients into a single, unified `ApiClient` to enforce a consistent pattern for all HTTP requests.
- [Core]: Unified all data models into canonical Zod v4 schemas under
  `src/lib/schemas/` and removed the redundant `src/types/` and `src/schemas/` directories to establish a single source of truth for data contracts and runtime validation.

## [0.2.1] - 2025-11-01

### [0.2.1] Added

- Next.js route `src/app/auth/callback/route.ts` exchanges OAuth `code` for session
- Login/Register use `@supabase/auth-ui-react` blocks (email/password + OAuth)
- FastAPI SSE chat endpoint `POST /api/chat/stream` (streams token deltas; `text/event-stream`)
- Next.js route `GET /api/attachments/files` with `next: { tags: ['attachments'] }` for SSR reads
- Upstash rate limiting for attachments upload route (enabled when `UPSTASH_REDIS_REST_URL|TOKEN` are set)
- Supabase typed helpers (`insertSingle`, `updateSingle`) with unit tests
- Trips repository tests and `use-chat-ai` smoke test
- ADR-0019 Canonicalize chat via FastAPI; updated AI SDK spec to match
- Session resume spec to simplify context restore
- Native AI SDK v5 chat route at `src/app/api/chat/route.ts` (streams UI messages via toUIMessageStreamResponse)
- Example AI SDK tool (`confirm`) with Zod input schema in chat route
- Next.js 16 caching defaults: enabled `cacheComponents` in `next.config.ts`; turned on `turbopackFileSystemCacheForDev`
- Supabase auth confirmation route at `src/app/auth/confirm/route.ts` using `@supabase/ssr`
- Upstash Redis helper `src/lib/redis.ts` with `getRedis()` and `incrCounter()` utilities (uses REST client for Edge compatibility)
- Suspense wrappers on app and dashboard layouts to satisfy Next 16 prerender rules with Cache Components
- Trip repository `src/lib/repositories/trips-repo.ts` for typed Supabase CRUD and UI mapping
- DuffelProvider (httpx, Duffel API v2) for flight search and booking; returns raw provider dicts mapped to canonical `FlightOffer` via the existing mapper (`tripsage_core.models.mappers.flights_mapper`)
- Optional Duffel auto‑wiring in `get_flight_service()` when `DUFFEL_ACCESS_TOKEN` (or legacy `DUFFEL_API_TOKEN`) is present
- Unit tests: provider (no‑network) and FlightService+provider mapping/booking paths; deterministic and isolated
- ADR-0012 documenting canonical flights DTOs and provider convergence
- Dashboard regression coverages: async unit tests for `DashboardService`, refreshed HTTP router tests, and an integration harness exercising the new schema
- Async unit tests for accommodation tools covering search/detail/booking flows via `ToolContext` mocks
- Supabase initialization regression tests covering connection verification, schema discovery, and sample data helpers (no-network stubs)
- Supabase Realtime Authorization policies and helpers (private channels, topic helpers, indexes):
  - supabase/migrations/20251027_01_realtime_policies.sql
  - supabase/migrations/20251027_02_realtime_helpers.sql
- Edge Functions deployed to new project (<PROJECT_REF>):
  - trip-notifications, file-processing, cache-invalidation, file-processor
- Migration prepared to upsert webhook_config endpoints to deployed functions (inactive by default):
  - supabase/migrations/20251028_01_update_webhook_configs.sql
- Frontend Realtime singleton client: `getBrowserClient()` exported from `frontend/src/lib/supabase/client.ts` to unify token and channel behavior across the app.
- Realtime token lifecycle: `RealtimeAuthProvider` now calls `supabase.realtime.setAuth(token)` on login and clears on logout/unmount.
- Chat store Realtime wiring with typed subscriptions for `chat:message`, `chat:message_chunk`, `chat:typing`, and `agent_status_update`.
- Base schema consolidated into authoritative migration and applied:
  - supabase/migrations/20251027174600_base_schema.sql
- Storage infrastructure migration (guarded) with buckets, queues, versioning, and RLS:
  - supabase/migrations/202510271702_storage_infrastructure.sql
  - Helpers moved to `public.*` schema to avoid storage schema ACL issues
- Repo linked to new Supabase project ref via CLI: `npx supabase link --project-ref <PROJECT_REF>`

- Makefile targets to drive Supabase workflows end-to-end:
  - `supa.link`, `supa.secrets-min`, `supa.secrets-upstash`, `supa.secrets-webhooks`, `supa.db.push`,
    `supa.migration.list`, `supa.migration.repair`, `supa.functions.deploy-all`, `supa.fn.deploy`, `supa.fn.logs`.
  - Includes deploy helper to rename `deno.lock -> deno.lock.v5` for the CLI bundler.
- Operator runbooks (developer-focused, command-first):
- `docs/operations/supabase-project-setup.md` — create/link/configure project; secrets; migrations; deploy; verify.
- `docs/operations/supabase-repro-deploy.md` — single-pass reproducible deployment sequence.
- Per-function Deno import maps + lockfiles:
  - Added `deno.json` and generated `deno.lock.v5` for: `trip-notifications`, `file-processing`, `cache-invalidation`, `file-processor`.

### [0.2.1] Changed

- Next.js middleware uses `@supabase/ssr` `createServerClient` + `auth.getUser()` with cookie sync
- Frontend hooks derive user via `supabase.auth.getUser()` (no React auth context)
- `useAuthenticatedApi` injects `Authorization` from supabase-js session/refresh
- API key management endpoints consolidated under `/api/keys`; `/api/user/keys` has been removed. Update downstream clients, firewall allowlists, and automation scripts to the new path before rollout.
- Supabase SSR client: validate `NEXT_PUBLIC_SUPABASE_URL|ANON_KEY`; wrap `cookies().setAll` in try/catch
- Next proxy: guard cookie writes with try/catch
- Edge Functions: upgraded runtime deps and import strategy
  - Deno std pinned to `0.224.0`; `@supabase/supabase-js` pinned to `2.76.1`
  - Refactored function imports to use import-map aliases (`std/http/server.ts`, `@supabase/supabase-js`)
  - Simplified per-function import maps to rely on `supabase-js` for internals; removed unnecessary explicit @supabase sub-packages from maps
  - Redeployed all functions (trip-notifications, file-processing, cache-invalidation, file-processor)
- Documentation: added setup and reproducible deployment guides and linked them from `docs/index.md`
- Chat hook (`use-chat-ai`):
  - Switch to streaming via `/api/chat/stream`
  - Add `AbortController` with 60s timeout
  - Fix session ID assignment after `createSession`
  - Use immutable Map updates; include `sessions` in `sendMessage` deps
- Attachments upload route: keep `revalidateTag('attachments', 'max')`; forward `Authorization` header
- Tailwind v4: replaced `bg-opacity-75` with `bg-black/75` in agent health UI
- Tailwind v4: ran upgrade tool and verified CSS-first config; postcss plugin in place
- Frontend deps: upgraded to Zod v4 and @hookform/resolvers v5; adapted code to new error and record APIs
- AI SDK route: fixed error handler to use `onError` returning string
- Supabase client usage in store: corrected imports, aligned with centralized repo functions
- Tailwind v4 verification fixes: replaced `<img>` with `next/image` for MFA QR code; converted interactive `<div>`s to `<button>`s in message attachments; added explicit radix to `Number.parseInt` calls
- Additional `<img>` tags with `next/image` in search cards; added unique IDs via `useId` for inputs
- Tailwind CSS v4: ran `npx @tailwindcss/upgrade` and confirmed CSS-first setup via `@import \"tailwindcss\";` in `src/app/globals.css`; kept `@tailwindcss/postcss` and removed legacy Turbopack flags from the `dev` script
- Minor Tailwind v4 compatibility: updated some `outline-none` usages to `outline-hidden` in UI components
- UI Button: fixed `asChild` cloning to avoid nested anchors and preserve parent className; merged Google-style `@fileoverview` JSDoc
- Testing: stabilized QuickActions, TripCard, user-store, and agent monitoring suites
  - QuickActions: replaced brittle class queries; verified links and focus styles
  - TripCard: deterministic date formatting (UTC) and flexible assertions
  - User store: derived fields (`displayName`, `hasCompleteProfile`, `upcomingDocumentExpirations`) computed and stored for deterministic reads; tests updated
  - Agent monitoring: aligned tests with ConnectionStatus variants; use `variant=\"detailed\"` for connected-state assertions
- Docs: ensured new/edited files include `@fileoverview` with concise technical descriptions
- Frontend API routes now default to FastAPI at `http://localhost:8001` and unified paths (`/api/chat`, `/api/attachments/*`)
- Attachments API now revalidates the `attachments` cache tag for both single and batch uploads before returning responses
- Chat domain canonicalized on FastAPI ChatService; removed the Next.js native chat route. Frontend hook now calls `${NEXT_PUBLIC_API_URL}/api/v1/chat/` directly and preserves authentication via credentials
- Dynamic year rendering on the home page moved to a small client component to avoid server prerender time coupling under Cache Components
- Centralized Supabase typed insert/update via `src/lib/supabase/typed-helpers.ts`; updated hooks to use helpers
- Chat UI prefers `message.parts` when present; removed ad-hoc adapter in `use-chat-ai` sync
- Trip store now routes create/update through the typed repository; removed direct Supabase writes from store
- Removed Python agents and orchestration: `tripsage.agents`, `tripsage.orchestration`, and `tripsage.tools` directories deleted as functionality migrated to TypeScript AI SDK v6 in frontend
- Simplified `ChatAgent` to delegate to the new base workflow while exposing async history/clearing helpers backed by `ChatService` with local fallbacks
- Flight agent result formatting updated to use canonical offer fields (airlines, outbound_segments, currency/price)
- Documentation (developers/operators/architecture) updated to \"Duffel API v2 via thin provider,\" headers and env var usage modernized, and examples aligned to canonical mapping
- Dashboard analytics stack simplified: `DashboardService` emits only modern dataclasses, FastAPI routers consume the `metrics/services/top_users` schema directly, and rate limiting now tolerates missing infrastructure dependencies
- Migrated chat messaging from custom WebSocket client to Supabase Realtime broadcast channels with private topics (`user:{sub}`, `session:{uuid}`)
- Updated hooks to use the shared browser Supabase client:
  - `use-realtime-channel`, `use-websocket-chat`, `use-agent-status-websocket` now import `getBrowserClient()`
- Chat UI connection behavior: resubscribe on session changes to avoid stale channel topics
- Admin configuration manager: removed browser WebSocket and simplified to save-and-refresh (Option A) pending optional Realtime wiring
- Backend OpenAPI/README documentation updated to describe Supabase Realtime (custom WS endpoints removed from docs)
- `tripsage.tools.accommodations_tools` now accepts `ToolContext` inputs, validates registry dependencies, and exposes tool wrappers alongside plain coroutine helpers
- Web search tooling replaced ad-hoc fallbacks with strict Agents SDK usage and literal-typed context sizing; batch helper now guards cache failures
- Web crawl helpers simplified to use `WebCrawlService` exclusively, centralizing error normalization and metrics recording
- OTEL decorators use overload-friendly typing so async/sync instrumentation survives pyright + pylint enforcement
- Database bootstrap hardens Supabase RPC handling, runs migrations via lazy imports, and scopes discovery to `supabase/migrations` with offline recording
- Accommodation stack now normalizes MCP client calls (keyword-only), propagates canonical booking/search metadata, and validates external listings via `model_validate`
- WebSocket router refactored around a shared `MessageContext`, consolidated handlers, and IDNA-aware origin validation while keeping dependencies Supabase-only
- API service DI now uses FastAPI `app.state` singletons via `tripsage/app_state.AppServiceContainer`:
  - Lifespan constructs and tears down cache, Google Maps, database, and related services in a typed container
  - Dependency providers (`tripsage/api/core/dependencies.py`) retrieve services from the container, eliminating bespoke registry lookups
  - A shared `ChatAgent` instance initialises during lifespan and is exposed through `app.state.chat_agent` for WebSocket handlers
- Dashboard Service refactored to eliminate N+1 queries, added 5-minute TTL caching, safe percentile calculations, removed redundant factory functions and duplicate model definitions, added cached computed properties; reduced from ~1200 to 846 lines

### [0.2.1] Refactor

- **[Models]:** Consolidated all duplicated data models for Trip, Itinerary, and Accommodation into canonical representations within `tripsage_core`. API schemas in `tripsage/api/schemas/` have been removed to enforce a single source of truth.
  - Merged ValidationResult and ServiceHealthCheck into ApiValidationResult for DRY compliance.
  - Verification: Single model used in both validation and health methods; tests cover all fields without duplication errors.
- **[API]:** All routers now rely on dependency helpers (e.g., `TripServiceDep`, `MemoryServiceDep`) sourced from the lifespan-managed `AppServiceContainer`, eliminating inline service instantiation across agents, attachments, accommodations, flights, itineraries, keys, destinations, and trips.
- **[Orchestration]:** LangGraph tools register the shared services container via `set_tool_services`, removing the final `ServiceRegistry` usage and guaranteeing tool invocations reuse the same singletons as the API.
- **Agents/DI:** Standardized on FastAPI app.state singletons, eliminating ServiceRegistry for simpler, lifespan-managed dependencies.
- **API/Schemas:** Centralized memory and attachments request/response models under `tripsage/api/schemas`, added health schemas, and moved trip search params to schemas; routers import these models and declare explicit `response_model`s.
- **API/Schemas (feature-first):** Completed migration from `schemas/{requests,responses}` to feature-first modules for memory, attachments, trips, activities, search, and realtime dashboard. Deleted legacy split directories and updated all imports.
- **Realtime Dashboard:** Centralized realtime DTOs and added typed responses for broadcast/connection endpoints.
- **Search Router:** UnifiedSearchRequest moved to feature-first schema with back-compat fields; analytics endpoint returns `SearchAnalyticsResponse`.
- **Attachments Router:** List endpoint now returns typed `FileListResponse` with `FileMetadataResponse` entries (service results adapted safely).
- **Trip Security:** Tightened types and returns for `TripAccessResult`; fixed permission comparison typing.
- **Middlewares:** Corrected type annotations (Awaitable[Response]) and Pydantic ConfigDict usage to satisfy pyright and Pydantic v2.

### [0.2.1] Fixed (DI migration sweep)

- Memory router endpoints updated for SlowAPI: rate-limited routes accept `request` and
  where applicable `response`; unit tests unwrap decorators and pass synthetic Request
  objects to avoid false negatives.
- Keys router status mapping aligned to domain validation: RATE_LIMITED → 429,
  INVALID/FORMAT_ERROR → 400, SERVICE_ERROR → 500; metrics endpoint now returns `{}` on
  provider failure instead of raising in tests.
- Orchestration tools (geocode/weather/web_search) resolve DI singletons from the
  shared container instead of instantiating services, ensuring consistent configuration
  and testability.
- Trips smoke test stub returns a UUID string, fixing response adaptation.
- Test configuration: removed non-existent `pytest-slowapi`; added `benchmark` marker to
  satisfy `--strict-markers`.

### [0.2.1] Removed

- Removed unused `SimpleSessionMemory` dep from `dependencies.py`; use `request.state` or `MemoryService` for session data.
- Legacy Supabase schema sources and scripts removed:
  - Deleted `supabase/schemas/` and `supabase/storage/` (replaced by migrations)
  - Deleted `supabase/deploy_database_schema.py`, `supabase/validate_database_schema.py`, `supabase/test_database_integration.py`
- Deleted `frontend/src/contexts/auth-context.tsx` and all imports
- Deleted `frontend/src/components/providers/supabase-provider.tsx` and layout wrapper
- Removed legacy callback page `frontend/src/app/(auth)/callback/page.tsx` and context-dependent tests
- Deleted broken duplicate ADR file `docs/adrs/adr-0012-slowapi-aiolimiter-migration.md` (superseded by ADR-0021)
- Removed unused AI SDK client dependencies (`ai`, `@ai-sdk/react`, `@ai-sdk/openai`) from frontend/package.json
- Removed legacy middleware tests referencing `middleware.ts` after migrating to the Next 16 `proxy` convention (final-only policy, no legacy paths retained)
- Removed the entire `tripsage/models/` directory, removing all legacy data models associated with the deprecated MCP architecture to eliminate duplication
- Removed legacy MCP components, including the generic `AccommodationMCPClient` and the `ErrorHandlingService`, to complete the migration to a direct SDK architecture
- Removed the custom performance metrics system in `tripsage/monitoring` and standardized all metrics collection on the OpenTelemetry implementation to use industry best practices
- Removed inbound rate limiting on SlowAPI (with `limits` async storage) and outbound throttling on `aiolimiter`. Removed the legacy custom `RateLimitMiddleware` and associated modules/tests
- Removed the custom `ServiceRegistry` module under `tripsage/config` and its dependent tests to simplify dependency management
- Removed `CoreMCPError`; MCP-related failures now surface as `CoreExternalAPIError` with appropriate context
- Removed legacy Google Maps dict-shaped responses and all backward-compatible paths in services/tests
- Removed module-level singletons for Google Maps and Activity services (`get_google_maps_service`, `get_activity_service`) and their `close_*` helpers; final-only DI now required
- Removed deprecated exports in `tripsage_core/services/external_apis/__init__.py` for maps/weather/webcrawl `get_*`/`close_*` helpers removed; use DI/constructors

### [0.2.1] Fixed

- FastAPI `AuthenticationMiddleware` now has corrected typing, Pydantic v2 config, Supabase token validation via `auth.get_user`, and unified responses
- Base agent node logging now emits the full exception message, keeping orchestration diagnostics actionable
- Google Maps integration returns typed models end-to-end:
  - New Pydantic models (`tripsage_core/models/api/maps_models.py`)
  - `GoogleMapsService` now returns typed models and removes custom HTTP logic
  - `LocationService` and `ActivityService` consume typed APIs only and use constructor DI
  - `tripsage/app_state.AppServiceContainer` injects `GoogleMapsService` and `CacheService` into `ActivityService`; API routers construct services explicitly (no globals)
  - Unit/integration tests rewritten for typed returns and deprecated suites removed
- Removed the legacy Duffel adapter (`tripsage_core/services/external_apis/flights_service.py`)
- Deleted the duplicate flight DTO module (`tripsage_core/models/api/flights_models.py`) and its re-exports
- Removed the obsolete integration test referencing the removed HTTP client (`tests/integration/external/test_duffel_integration.py`)
- Cleaned dashboard compatibility shims (legacy `DashboardData` fields, `ApiKeyValidator`/`ApiKeyMonitoringService` aliases) and the unused flights mapper module (`tripsage_core/models/mappers`)
- Resolved linting and typing issues in touched flight tests and orchestration node; `pyright` and `pylint` now clean on the updated scope
- WebSocket integration/unit test suites updated for the refactored router (async dependency overrides, Supabase wiring, Unicode homograph coverage)
- Realtime integration/unit test suites aligned to Supabase Realtime channels (no custom WebSocket router)
- Supabase migrations reconcile remote/local history and document the `migration repair` workflow to resolve mismatched version formats (8–12 digit IDs)
- `supabase/config.toml` updated for CLI v2 compatibility (removed invalid keys; normalized `[auth.email]` flags; set `db.major_version=17`) and unused OAuth providers ([auth.external.google/github].enabled=false) disabled to reduce CLI warnings in CI
- Realtime policy migration made idempotent with `pg_policies` guards; session policies created only when `public.chat_sessions` exists
- Storage migration guarded for fresh projects: policies referencing `public.file_attachments` and `public.trips` wrap in conditional DO blocks; functions reference application tables at runtime only
- Realtime helpers/policies and storage migration filenames normalized to 2025-10-27 timestamps
- Edge Functions toolchain hardened:
  - Standardized per-function import maps (`deno.json`) using `std@0.224.0` and `@supabase/supabase-js@2.76.1`
  - Regenerated Deno v5 lockfiles (`deno.lock.v5`) for all functions; preserved for deterministic local dev while the CLI bundler ignores v5 locks
  - Unified deploy workflow via Makefile; CLI updated to v2.54.x on local environments

### [0.2.1] Breaking Changes

- Removed React auth context; SSR + route handlers are required for auth; OAuth and email confirm flows now terminate in server routes
- **ChatService Alignment**: ChatService finalized to DI-only (no globals/event-loop hacks); public methods now directly call DatabaseService helpers: `create_chat_session`, `create_chat_message`, `get_user_chat_sessions`, `get_session_messages`, `get_chat_session`, `get_message_tool_calls`, `update_tool_call`, `update_session_timestamp`, `end_chat_session`
- **ChatService Alignment**: Removed router-compat wrappers (`list_sessions`, `create_message`, `delete_session`) and legacy parameter orders; canonical signatures are:
  - `get_session(session_id, user_id)`, `get_messages(session_id, user_id, limit|offset)`, `add_message(session_id, user_id, MessageCreateRequest)`
- **ChatService Alignment**: Router `tripsage/api/routers/chat.py` now accepts JSON bodies (no query-param misuse); `POST /api/chat/sessions` returns 201 Created; endpoints wired to the new service methods
- **ChatService Alignment**: OTEL decorators added on ChatService public methods with low-cardinality attrs; test env skips exporter init to avoid network failures
- **ChatService Alignment**: SecretStr respected for OpenAI key; sanitized content + metadata validation retained
- **ChatService Alignment**: Tests updated to final-only contracts (unit+integration) to reflect JSON bodies and new method signatures

### [0.2.1] Notes

- Tailwind v4 verification of utility coverage is in progress; further class name adjustments
  will be tracked in the Tailwind v4 spec and reflected here upon completion.
- For server-originated events, use Supabase Realtime REST API or Postgres functions (`realtime.send`) with RLS-backed policies.
- Presence is not yet used; typing indicators use broadcast. Presence can be adopted later without API changes.

## [0.2.0] - 2025-10-20

### [0.2.0] Added

- Added Pydantic-native trip export response with secure token and expiry; supports `export_format` plus optional `format` kw
- Added date/time normalization helpers in trips router for safe coercion and ISO handling

### [0.2.0] Changed

- Updated trips router to use Pydantic v2 `model_validate` for core→API mapping; eliminated ad‑hoc casting
- Updated `/trips` list and `/trips/search` now return `TripListResponse` with `TripListItem` entries; OpenAPI schema reflects these models
- Updated collaboration endpoints standardize on `TripService` contracts (`share_trip`, `get_trip_collaborators`, `unshare_trip`); responses use `TripCollaboratorResponse`
- Updated authorization semantics unified: 403 (forbidden), 404 (not found), 500 (unexpected error)
- Updated `TripShareRequest.user_emails` to support batch flows (min_length=0, max_length=50)

### [0.2.0] Removed

- Removed dict-shaped responses in list/search paths; replaced with typed response models
- Removed scattered UUID/datetime parsing; centralized to helpers

### [0.2.0] Fixed

- Fixed collaboration endpoint tests aligned to Pydantic v2 models; removed brittle assertions

### [0.2.0] Security

- Secured trip export path validated; formats restricted to `pdf|csv|json`

### [0.2.0] Breaking Changes

- **API Response Format**: Clients parsing list/search responses as arbitrary dicts should align to the documented `TripListResponse` schema (field names unchanged; server typing improved)

## [0.1.0] - 2025-06-21

### [0.1.0] Added

- Added unified Database Service consolidating seven services into a single optimized module
- Added PGVector HNSW indexing (vector search up to ~30x faster vs. prior)
- Added Supavisor-backed LIFO connection pooling with safe overflow controls
- Added enterprise WebSocket stack: Redis-backed sessions, parallel broadcasting, bounded queues/backpressure, and load shedding (validated at >10k concurrent connections)
- Added centralized event serialization helper to remove duplication
- Added health checks and performance probes for core services

### [0.1.0] Changed

- Updated query latency improved (~3x typical); vector search ~30x faster; startup 60–70% faster
- Updated memory usage reduced ~35–50% via compression/caching and leaner initialization
- Updated async-first execution replaces blocking hot paths; broadcast fan-out ~31x faster for 100 clients
- Updated configuration flattened and standardized (single settings module)
- Updated observability unified with metrics and health endpoints across services
- Navigation: added "/attachments" link in main navbar
- ADR index grouped By Category in docs/adrs/README.md
- Docs: SSE client expectations note in docs/users/feature-reference.md
- Docs: Upstash optional edge rate-limit section in docs/operations/deployment-guide.md
- Confirm upload routes use Next 16 API `revalidateTag('attachments', 'max')` for Route Handlers
- Frontend copy/comments updated to reference two-arg `revalidateTag` where applicable
- Corrected `revalidateTag` usage in attachments upload handler and docs

### [0.1.0] Removed

- Legacy Supabase schema sources and scripts removed:
  - Deleted `supabase/schemas/` and `supabase/storage/` (replaced by migrations)
  - Deleted `supabase/deploy_database_schema.py`, `supabase/validate_database_schema.py`, `supabase/test_database_integration.py`
- Removed complex tool registry and redundant orchestration/abstraction layers
- Removed nested configuration classes and legacy database service implementations
- Removed deprecated dependencies and unused modules
- tests(frontend): deleted/replaced deprecated and brittle tests asserting raw HTML structure and Tailwind class lists; removed NODE_ENV mutation based tests.

### [0.1.0] Fixed

- Fixed memory leaks in connection pools and unbounded queues
- Fixed event loop stalls caused by blocking operations in hot paths
- Fixed redundant validation chains that increased latency

### [0.1.0] Security

- Secured Pydantic-based input validation for WebSocket messages
- Secured message size limits and multi-level rate limiting (Redis-backed)
- Secured origin validation (CSWSH protection), tightened JWT validation, and improved audit logging

### [0.1.0] Breaking Changes

- **Database APIs**: Consolidated DB APIs; unified configuration module; synchronous paths removed (migrate to async interfaces)

### [0.1.0] Testing

- Frontend testing modernization (Vitest + RTL):
  - Rewrote flaky suites to use `vi.useFakeTimers()`/`advanceTimersByTimeAsync` and resilient queries.
  - Updated suites: `ui-store`, `upcoming-flights`, `user-store-fixed`, `personalization-insights`, `trip-card`.
  - Relaxed brittle DOM assertions in error-boundary integration tests to assert semantics in jsdom.
  - Migrated imports to Zod schema modules; ensured touched files include `@fileoverview` and accurate JSDoc on exported helpers/config.
- Frontend tests: deterministic clock helper `src/test/clock.ts` and RTL config helper `src/test/testing-library.ts` with JSDoc headers.
- Vitest configuration: default jsdom, controlled workers (forks locally, threads in CI), conservative timeouts, coverage (v8 + text/json/html/lcov).
- tests(frontend): stabilize async hooks and UI suites
  - hooks: aligned `use-authenticated-api` tests with final ApiError type; fixed 401 refresh and non-401 branches; added fake-timer flushing for retries
  - hooks: rewrote `use-activity-search` tests to match final minimal hook; removed legacy API/store assertions
  - hooks: fixed `use-destination-search` stability by memoizing actions; updated tests for function reference stability
  - app: simplified error-boundaries integration tests; removed brittle `process.env` mutation; assert behavior independent of env
  - app: profile page tests now mock `useAuthStore` + `useUserProfileStore`; switched to RTL `userEvent` and ARIA queries; removed class-name assertions
- components: normalized skeleton assertions to role="status" with accessible name
- tests(websocket): replaced brittle environment-coupled suite with deterministic smoke tests invoking internal handlers; verification covers connect flow and metrics without relying on global WebSocket
- tests(profile/preferences): removed outdated suite asserting internal store interactions and brittle combobox text; to be reintroduced as focused integration tests in a follow-up
- chore(vitest): prefer `--pool=forks` locally and threads in CI; tuned timeouts and bail per `vitest.config.ts`
- Stabilized profile settings tests:
  - `account-settings-section.test.tsx`: deterministic confirmation/cancel flows; removed overuse of timers and brittle waitFor blocks; aligned toast mocking to global setup.
  - `security-section.test.tsx`: rewrote to use placeholders over labels, added precise validation assertions, reduced timer reliance, and removed legacy expectations that no longer match the implementation.
- Modernized auth UI tests:
  - `reset-password-form.test.tsx`: aligned to HTML5 required validation and auth-context error model; added loading-state test via context; removed brittle id assertions.
- Simplified trips UI tests:
  - `itinerary-builder.test.tsx`: avoided combobox portal clicks; added scoped submit helpers; exercised minimal add flow and activities; removed flaky edit-dialog flows.
- Applied @fileoverview headers and JSDoc-style comments to updated suites per Google TS style.
- docs(jsdoc): ensured updated files include clear @fileoverview descriptions following Google style

### [0.1.0] Tooling

- Biome formatting/lint fixes across touched files; `vitest.config.ts` formatting normalized.
- Legacy Python planning tools removed:
  - Deleted `tripsage/tools/planning_tools.py` and purged references/tests.

[Unreleased]: https://github.com/BjornMelin/tripsage-ai/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/BjornMelin/tripsage-ai/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/BjornMelin/tripsage-ai/compare/v0.2.1...v1.0.0
[0.2.1]: https://github.com/BjornMelin/tripsage-ai/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/BjornMelin/tripsage-ai/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/BjornMelin/tripsage-ai/releases/tag/v0.1.0
