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

### Changed

- Flight agent result formatting updated to use canonical offer fields (airlines, outbound_segments, currency/price).
- Documentation (developers/operators/architecture) updated to “Duffel API v2 via thin provider,” headers and env var usage modernized, and examples aligned to canonical mapping.

### Deprecated

### Removed

- Legacy Duffel adapter (`tripsage_core/services/external_apis/flights_service.py`).
- Duplicate flight DTO module (`tripsage_core/models/api/flights_models.py`) and its re‑exports.
- Obsolete integration test referencing the removed HTTP client (`tests/integration/external/test_duffel_integration.py`).

### Fixed

- Linting/typing issues in touched flight tests and orchestration node; pyright/pylint clean on changed scope.

### Security

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
