# Changelog

All notable changes to TripSage will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- DuffelProvider (httpx, Duffel API v2) for flight search and booking; returns raw provider dicts mapped to canonical `FlightOffer` via the existing mapper (`tripsage_core.models.mappers.flights_mapper`).
- Optional Duffel auto‑wiring in `get_flight_service()` when `DUFFEL_ACCESS_TOKEN` (or legacy `DUFFEL_API_TOKEN`) is present.
- Unit tests: provider (no‑network) and FlightService+provider mapping/booking paths; deterministic and isolated.
- ADR-0012 documenting canonical flights DTOs and provider convergence.
- Dashboard regression coverages: async unit tests for `DashboardService`, refreshed HTTP router tests,
  and an integration harness exercising the new schema.
- Async unit tests for accommodation tools covering search/detail/booking flows via `ToolContext` mocks.
- Supabase initialization regression tests covering connection verification, schema discovery, and sample data helpers (no-network stubs).

### Changed

- Rebuilt `tripsage.agents.base.BaseAgent` around LangGraph orchestration with ChatOpenAI fallback execution, memory hydration, and periodic conversation summarization.
- Simplified `ChatAgent` to delegate to the new base workflow while exposing async history/clearing helpers backed by `ChatService` with local fallbacks.
- Flight agent result formatting updated to use canonical offer fields (airlines, outbound_segments, currency/price).
- Documentation (developers/operators/architecture) updated to “Duffel API v2 via thin provider,” headers and env var usage modernized, and examples aligned to canonical mapping.
- Dashboard analytics stack simplified: `DashboardService` emits only modern dataclasses, FastAPI routers consume the `metrics/services/top_users`
  schema directly, and rate limiting now tolerates missing infrastructure dependencies.
- `tripsage.tools.accommodations_tools` now accepts `ToolContext` inputs, validates registry dependencies, and exposes tool wrappers alongside plain coroutine helpers.
- Web search tooling replaced ad-hoc fallbacks with strict Agents SDK usage and literal-typed context sizing; batch helper now guards cache failures.
- Web crawl helpers simplified to use `WebCrawlService` exclusively, centralizing error normalization and metrics recording.
- OTEL decorators use overload-friendly typing so async/sync instrumentation survives pyright + pylint enforcement.
- Database bootstrap hardens Supabase RPC handling, runs migrations via lazy imports, and scopes discovery to `supabase/migrations` with offline recording.
- Accommodation stack now normalizes MCP client calls (keyword-only), propagates canonical booking/search metadata, and validates external listings via `model_validate`.
- WebSocket router refactored around a shared `MessageContext`, consolidated handlers, and IDNA-aware origin validation while keeping dependencies Supabase-only.
- API service DI now uses the global `ServiceRegistry` in `tripsage/config/service_registry.py`:
  - Lifespan registers singletons for `cache` and `google_maps`.
  - New adapters provide `activity` and `location` services from registry-managed deps.
  - API dependency providers (`tripsage/api/core/dependencies.py`) resolve via registry (no `app.state` coupling for these services).

### Deprecated

### Removed

- [Core Models]: Deleted the entire `tripsage/models/` directory, removing all legacy data models associated with the deprecated MCP architecture to eliminate duplication.
- [Core Services]: Deleted legacy MCP components, including the generic `AccommodationMCPClient` and the `ErrorHandlingService`, to complete the migration to a direct SDK architecture.
- [Observability]: Removed the custom performance metrics system in `tripsage/monitoring` and standardized all metrics collection on the OpenTelemetry implementation to use industry best practices.
- [API]: Standardized inbound rate limiting on SlowAPI (with `limits` async storage) and outbound throttling on `aiolimiter`. Removed the legacy custom `RateLimitMiddleware` and associated modules/tests.
- [Architecture]: Removed the custom `ServiceRegistry` module under `tripsage/config` and its dependent tests to simplify dependency management.
- [Exceptions]: Removed `CoreMCPError`; MCP-related failures now surface as `CoreExternalAPIError` with appropriate context.

- Legacy Google Maps dict-shaped responses and all backward-compatible paths in services/tests.
- Module-level singletons for Google Maps and Activity services (`get_google_maps_service`,
  `get_activity_service`) and their `close_*` helpers; final-only DI now required.
- Deprecated exports in `tripsage_core/services/external_apis/__init__.py` for maps/weather/webcrawl `get_*`/`close_*` helpers removed; use DI/constructors.

### Fixed

- Base agent node logging now emits the full exception message, keeping orchestration diagnostics actionable.
- Consolidated, typed Google Maps integration:
  - New Pydantic models (`tripsage_core/models/api/maps_models.py`).
  - `GoogleMapsService` now returns typed models and removes custom HTTP logic.
  - `LocationService` and `ActivityService` refactored to consume typed API only (no legacy code) and use constructor DI.
  - `tripsage/agents/service_registry.py` wires `ActivityService` via injected `GoogleMapsService` and `CacheService`.
  - `tripsage/api/routers/activities.py` constructs services explicitly (no globals).
  - Unit/integration tests rewritten for typed returns; deprecated suites removed.

- Legacy Duffel adapter (`tripsage_core/services/external_apis/flights_service.py`).
- Duplicate flight DTO module (`tripsage_core/models/api/flights_models.py`) and its re‑exports.
- Obsolete integration test referencing the removed HTTP client (`tests/integration/external/test_duffel_integration.py`).
- Dashboard compatibility shims (legacy `DashboardData` fields, `ApiKeyValidator`/`ApiKeyMonitoringService` aliases) and the unused flights mapper module (`tripsage_core/models/mappers`).

### Fixed

- Linting/typing issues in touched flight tests and orchestration node; pyright/pylint clean on changed scope.
- WebSocket integration/unit test suites updated for the refactored router (async dependency overrides, Supabase wiring, Unicode homograph coverage).

### Security

### Chat Service Alignment (Breaking)

- ChatService finalized to DI-only (no globals/event-loop hacks); public methods now directly call DatabaseService helpers: `create_chat_session`, `create_chat_message`, `get_user_chat_sessions`, `get_session_messages`, `get_chat_session`, `get_message_tool_calls`, `update_tool_call`, `update_session_timestamp`, `end_chat_session`.
- Removed router-compat wrappers (`list_sessions`, `create_message`, `delete_session`) and legacy parameter orders; canonical signatures are:
  - `get_session(session_id, user_id)`, `get_messages(session_id, user_id, limit|offset)`, `add_message(session_id, user_id, MessageCreateRequest)`.
- Router `tripsage/api/routers/chat.py` now accepts JSON bodies (no query-param misuse); `POST /api/chat/sessions` returns 201 Created; endpoints wired to the new service methods.
- OTEL decorators added on ChatService public methods with low-cardinality attrs; test env skips exporter init to avoid network failures.
- SecretStr respected for OpenAI key; sanitized content + metadata validation retained.
- Tests updated to final-only contracts (unit+integration) to reflect JSON bodies and new method signatures.

## [2.1.0] - 2025-10-20

### Added

- Pydantic-native trip export response with secure token and expiry; supports `export_format` plus optional `format` kw.
- Date/time normalization helpers in trips router for safe coercion and ISO handling.

### Changed

- Refactored trips router to use Pydantic v2 `model_validate` for core→API mapping; eliminated ad‑hoc casting.
- `/trips` list and `/trips/search` now return `TripListResponse` with `TripListItem` entries; OpenAPI schema reflects these models.
- Collaboration endpoints standardize on `TripService` contracts (`share_trip`, `get_trip_collaborators`, `unshare_trip`); responses use `TripCollaboratorResponse`.
- Authorization semantics unified: 403 (forbidden), 404 (not found), 500 (unexpected error).
- Relaxed `TripShareRequest.user_emails` to support batch flows (min_length=0, max_length=50).

### Removed

- Dict-shaped responses in list/search paths; replaced with typed response models.
- Scattered UUID/datetime parsing; centralized to helpers.

### Fixed

- Collaboration endpoint tests aligned to Pydantic v2 models; removed brittle assertions.

### Security

- Trip export path validated; formats restricted to `pdf|csv|json`.

### Migration Notes (Breaking)

- Clients parsing list/search responses as arbitrary dicts should align to the documented `TripListResponse` schema (field names unchanged; server typing improved).

## [2.0.0] - 2025-06-21

### Added

- Unified Database Service consolidating seven services into a single optimized module.
- PGVector HNSW indexing (vector search up to ~30x faster vs. prior).
- Supavisor-backed LIFO connection pooling with safe overflow controls.
- Enterprise WebSocket stack: Redis-backed sessions, parallel broadcasting, bounded queues/backpressure, and load shedding (validated at >10k concurrent connections).
- Centralized event serialization helper to remove duplication.
- Health checks and performance probes for core services.

### Changed

- Query latency improved (~3x typical); vector search ~30x faster; startup 60–70% faster.
- Memory usage reduced ~35–50% via compression/caching and leaner initialization.
- Async-first execution replaces blocking hot paths; broadcast fan-out ~31x faster for 100 clients.
- Configuration flattened and standardized (single settings module).
- Observability unified with metrics and health endpoints across services.
- Breaking: consolidated DB APIs; unified configuration module; synchronous paths removed (migrate to async interfaces).

### Removed

- Complex tool registry and redundant orchestration/abstraction layers.
- Nested configuration classes and legacy database service implementations.
- Deprecated dependencies and unused modules.

### Fixed

- Memory leaks in connection pools and unbounded queues.
- Event loop stalls caused by blocking operations in hot paths.
- Redundant validation chains that increased latency.

### Security

- Pydantic-based input validation for WebSocket messages.
- Message size limits and multi-level rate limiting (Redis-backed).
- Origin validation (CSWSH protection), tightened JWT validation, and improved audit logging.

[Unreleased]: https://github.com/BjornMelin/tripsage-ai/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/BjornMelin/tripsage-ai/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/BjornMelin/tripsage-ai/releases/tag/v2.0.0
