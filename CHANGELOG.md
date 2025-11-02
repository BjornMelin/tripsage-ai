# Changelog

All notable changes to TripSage will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Dependency-injected handlers for App Router APIs:
  - Chat stream: `frontend/src/app/api/chat/stream/_handler.ts`
  - Keys (BYOK): `frontend/src/app/api/keys/_handlers.ts`
  - Sessions/messages: `frontend/src/app/api/chat/sessions/_handlers.ts`
- Attachment utilities and validation:
  - `frontend/src/app/api/_helpers/attachments.ts`
- Deterministic Vitest suites for handlers and adapter smokes:
  - Chat stream handler and route smokes under `frontend/src/app/api/chat/stream/__tests__/`
  - Keys and sessions handler tests under `frontend/src/app/api/keys/__tests__/` and `frontend/src/app/api/chat/sessions/__tests__/`
- Frontend agent guidelines for DI handlers, thin adapters, lazy RL, and testing:
  - `frontend/AGENTS.md`
- ADR documenting DI handlers + thin adapters testing strategy:
  - `docs/adrs/adr-0029-di-route-handlers-and-testing.md`
- Provider registry and resolution (server-only) returning AI SDK v6 `LanguageModel`:
  - `frontend/src/lib/providers/registry.ts` (`resolveProvider(userId, modelHint?)`)
  - `frontend/src/lib/providers/types.ts`, `frontend/src/lib/settings.ts`
- OpenRouter attribution headers support (`HTTP-Referer`, `X-Title`) sourced from env
- Vitest unit tests for registry precedence and attribution
  - `frontend/src/lib/providers/__tests__/registry.test.ts`
- Architecture docs: ADR and Spec for provider order, attribution, and SSR boundaries
  - `docs/adrs/2025-11-01-provider-registry.md`, `docs/specs/provider-registry.md`
- Dependency: `@ai-sdk/anthropic@3.0.0-beta.47`

### Changed

- Chat stream adapter now delegates to DI handler and builds the Upstash rate limiter lazily:
  - `frontend/src/app/api/chat/stream/route.ts`
- Keys and sessions adapters delegate to their DI handlers:
  - `frontend/src/app/api/keys/route.ts`
  - `frontend/src/app/api/chat/sessions/route.ts`
  - `frontend/src/app/api/chat/sessions/[id]/route.ts`
  - `frontend/src/app/api/chat/sessions/[id]/messages/route.ts`
- Vitest defaults tuned for stability and timeouts:
  - `frontend/vitest.config.ts` (unstubEnvs, threads, single worker)
  - `frontend/package.json` test scripts include short timeouts

### Fixed

- Resolved hanging API tests by:
  - Injecting a finite AI stream stub in handler tests (no open handles)
  - Building Upstash rate limiters lazily (no module‑scope side effects)
  - Guarding JSDOM‑specific globals in `frontend/src/test-setup.ts`
  - Using `vi.resetModules()` and env stubs before importing route modules

- Centralized BYOK provider selection; preference order: openai → openrouter → anthropic → xai
- OpenRouter and xAI wired via OpenAI-compatible client with per-user BYOK and required base URLs
- Registry is SSR-only (`server-only`), never returns or logs secret material

### Removed

- Python provider wrappers and tests removed (see Breaking Changes)
- FastAPI chat router and schemas removed; chat moved to Next.js AI SDK v6
  - Deleted: `tripsage/api/routers/chat.py`, `tripsage/api/schemas/chat.py`
  - Removed ChatAgent and chat service wiring: `tripsage/agents/chat.py`, ChatAgent initialization in `tripsage/api/main.py`, chat service from `tripsage/app_state.py`, ChatService from `tripsage_core/services/business/chat_service.py`
  - Deleted tests and fixtures tied to Python chat: `tests/integration/api/test_chat_streaming.py`, `tests/e2e/test_agent_config_flow.py`, `tests/fixtures/http.py`, and `tests/unit/agents/test_create_agent.py`

### Security

- Provider keys are fetched via server-side Supabase RPCs only; no client exposure
- OpenRouter attribution headers are non-sensitive and attached only when set

### Breaking Changes

- Removed legacy Python LLM provider modules and corresponding tests:
  - `tripsage_core/services/external_apis/llm_providers.py`
  - `tripsage_core/services/external_apis/providers/{openai_adapter.py, openrouter_adapter.py, anthropic_adapter.py, xai_adapter.py, token_budget.py, interfaces.py}`
  - `tests/unit/external/{test_llm_providers.py, test_providers.py, test_token_budget.py}`
- No backwards compatibility shims retained; registry is the final implementation
- Removed Python chat API entirely in favor of Next.js routes using AI SDK v6; any direct callers to `/api/chat/*` must use `/app/api/chat/stream` (Next.js) instead

## [2.2.0] - 2025-11-01

### Added

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
  - `docs/operators/supabase-project-setup.md` — create/link/configure project; secrets; migrations; deploy; verify.
  - `docs/operators/supabase-repro-deploy.md` — single-pass reproducible deployment sequence.
- Per-function Deno import maps + lockfiles:
  - Added `deno.json` and generated `deno.lock.v5` for: `trip-notifications`, `file-processing`, `cache-invalidation`, `file-processor`.

### Changed

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
- Rebuilt `tripsage.agents.base.BaseAgent` around LangGraph orchestration with ChatOpenAI fallback execution, memory hydration, and periodic conversation summarization
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

### Refactor

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

### Fixed (DI migration sweep)

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

### Deprecated

### Removed

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

### Fixed

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

### Security

### Breaking Changes

- Removed React auth context; SSR + route handlers are required for auth; OAuth and email confirm flows now terminate in server routes
- **ChatService Alignment**: ChatService finalized to DI-only (no globals/event-loop hacks); public methods now directly call DatabaseService helpers: `create_chat_session`, `create_chat_message`, `get_user_chat_sessions`, `get_session_messages`, `get_chat_session`, `get_message_tool_calls`, `update_tool_call`, `update_session_timestamp`, `end_chat_session`
- **ChatService Alignment**: Removed router-compat wrappers (`list_sessions`, `create_message`, `delete_session`) and legacy parameter orders; canonical signatures are:
  - `get_session(session_id, user_id)`, `get_messages(session_id, user_id, limit|offset)`, `add_message(session_id, user_id, MessageCreateRequest)`
- **ChatService Alignment**: Router `tripsage/api/routers/chat.py` now accepts JSON bodies (no query-param misuse); `POST /api/chat/sessions` returns 201 Created; endpoints wired to the new service methods
- **ChatService Alignment**: OTEL decorators added on ChatService public methods with low-cardinality attrs; test env skips exporter init to avoid network failures
- **ChatService Alignment**: SecretStr respected for OpenAI key; sanitized content + metadata validation retained
- **ChatService Alignment**: Tests updated to final-only contracts (unit+integration) to reflect JSON bodies and new method signatures

### Notes

- Tailwind v4 verification of utility coverage is in progress; further class name adjustments
  will be tracked in the Tailwind v4 spec and reflected here upon completion.
- For server-originated events, use Supabase Realtime REST API or Postgres functions (`realtime.send`) with RLS-backed policies.
- Presence is not yet used; typing indicators use broadcast. Presence can be adopted later without API changes.

## [2.1.0] - 2025-10-20

### Added

- Added Pydantic-native trip export response with secure token and expiry; supports `export_format` plus optional `format` kw
- Added date/time normalization helpers in trips router for safe coercion and ISO handling

### Changed

- Updated trips router to use Pydantic v2 `model_validate` for core→API mapping; eliminated ad‑hoc casting
- Updated `/trips` list and `/trips/search` now return `TripListResponse` with `TripListItem` entries; OpenAPI schema reflects these models
- Updated collaboration endpoints standardize on `TripService` contracts (`share_trip`, `get_trip_collaborators`, `unshare_trip`); responses use `TripCollaboratorResponse`
- Updated authorization semantics unified: 403 (forbidden), 404 (not found), 500 (unexpected error)
- Updated `TripShareRequest.user_emails` to support batch flows (min_length=0, max_length=50)

### Removed

- Legacy Supabase schema sources and scripts removed:
  - Deleted `supabase/schemas/` and `supabase/storage/` (replaced by migrations)
  - Deleted `supabase/deploy_database_schema.py`, `supabase/validate_database_schema.py`, `supabase/test_database_integration.py`

- Removed dict-shaped responses in list/search paths; replaced with typed response models
- Removed scattered UUID/datetime parsing; centralized to helpers

### Fixed

- Fixed collaboration endpoint tests aligned to Pydantic v2 models; removed brittle assertions

### Security

- Secured trip export path validated; formats restricted to `pdf|csv|json`

### Breaking Changes

- **API Response Format**: Clients parsing list/search responses as arbitrary dicts should align to the documented `TripListResponse` schema (field names unchanged; server typing improved)

## [2.0.0] - 2025-06-21

### Added

- Added unified Database Service consolidating seven services into a single optimized module
- Added PGVector HNSW indexing (vector search up to ~30x faster vs. prior)
- Added Supavisor-backed LIFO connection pooling with safe overflow controls
- Added enterprise WebSocket stack: Redis-backed sessions, parallel broadcasting, bounded queues/backpressure, and load shedding (validated at >10k concurrent connections)
- Added centralized event serialization helper to remove duplication
- Added health checks and performance probes for core services

### Changed

- Updated query latency improved (~3x typical); vector search ~30x faster; startup 60–70% faster
- Updated memory usage reduced ~35–50% via compression/caching and leaner initialization
- Updated async-first execution replaces blocking hot paths; broadcast fan-out ~31x faster for 100 clients
- Updated configuration flattened and standardized (single settings module)
- Updated observability unified with metrics and health endpoints across services

### Removed

- Legacy Supabase schema sources and scripts removed:
  - Deleted `supabase/schemas/` and `supabase/storage/` (replaced by migrations)
  - Deleted `supabase/deploy_database_schema.py`, `supabase/validate_database_schema.py`, `supabase/test_database_integration.py`

- Removed complex tool registry and redundant orchestration/abstraction layers
- Removed nested configuration classes and legacy database service implementations
- Removed deprecated dependencies and unused modules

### Fixed

- Fixed memory leaks in connection pools and unbounded queues
- Fixed event loop stalls caused by blocking operations in hot paths
- Fixed redundant validation chains that increased latency

### Security

- Secured Pydantic-based input validation for WebSocket messages
- Secured message size limits and multi-level rate limiting (Redis-backed)
- Secured origin validation (CSWSH protection), tightened JWT validation, and improved audit logging

### Breaking Changes

- **Database APIs**: Consolidated DB APIs; unified configuration module; synchronous paths removed (migrate to async interfaces)

[Unreleased]: https://github.com/BjornMelin/tripsage-ai/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/BjornMelin/tripsage-ai/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/BjornMelin/tripsage-ai/releases/tag/v2.0.0

- Navigation: added "/attachments" link in main navbar
- ADR index grouped By Category in docs/adrs/README.md
- Docs: SSE client expectations note in docs/users/feature-reference.md
- Docs: Upstash optional edge rate-limit section in docs/operators/deployment-guide-full.md
- Upload routes: confirm Next 16 API `revalidateTag('attachments', 'max')` for Route Handlers
- Frontend copy/comments updated to reference two-arg `revalidateTag` where applicable
- Corrected `revalidateTag` usage in attachments upload handler and docs
- Frontend tests: deterministic clock helper `src/test/clock.ts` and RTL config helper `src/test/testing-library.ts` with JSDoc headers.
- Vitest configuration: default jsdom, controlled workers (forks locally, threads in CI), conservative timeouts, coverage (v8 + text/json/html/lcov).
- Frontend testing modernization (Vitest + RTL):
  - Rewrote flaky suites to use `vi.useFakeTimers()`/`advanceTimersByTimeAsync` and resilient queries.
  - Updated suites: `ui-store`, `upcoming-flights`, `user-store-fixed`, `personalization-insights`, `trip-card`.
  - Relaxed brittle DOM assertions in error-boundary integration tests to assert semantics in jsdom.
  - Migrated imports to Zod schema modules; ensured touched files include `@fileoverview` and accurate JSDoc on exported helpers/config.
- Frontend legacy/back-compat artifacts:
  - `src/lib/api/validated-client.ts`.
  - `src/types/agent-status.ts`, `src/types/budget.ts` (replaced by `lib/schemas/*`).

### Testing and Frontend Cleanup

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
- docs(jsdoc): ensured updated files include clear @fileoverview descriptions following Google style

### Removed

- Legacy Supabase schema sources and scripts removed:
  - Deleted `supabase/schemas/` and `supabase/storage/` (replaced by migrations)
  - Deleted `supabase/deploy_database_schema.py`, `supabase/validate_database_schema.py`, `supabase/test_database_integration.py`
- tests(frontend): deleted/replaced deprecated and brittle tests asserting raw HTML structure and Tailwind class lists; removed NODE_ENV mutation based tests.

### Testing (frontend)

- Stabilized profile settings tests:
  - `account-settings-section.test.tsx`: deterministic confirmation/cancel flows; removed overuse of timers and brittle waitFor blocks; aligned toast mocking to global setup.
  - `security-section.test.tsx`: rewrote to use placeholders over labels, added precise validation assertions, reduced timer reliance, and removed legacy expectations that no longer match the implementation.
- Modernized auth UI tests:
  - `reset-password-form.test.tsx`: aligned to HTML5 required validation and auth-context error model; added loading-state test via context; removed brittle id assertions.
- Simplified trips UI tests:
  - `itinerary-builder.test.tsx`: avoided combobox portal clicks; added scoped submit helpers; exercised minimal add flow and activities; removed flaky edit-dialog flows.
- Applied @fileoverview headers and JSDoc-style comments to updated suites per Google TS style.

### Tooling

- Biome formatting/lint fixes across touched files; `vitest.config.ts` formatting normalized.
