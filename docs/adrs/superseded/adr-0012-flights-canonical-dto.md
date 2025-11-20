# ADR-0012: Canonical Flights DTOs and Service Convergence

**Version**: 1.0.0  
**Status**: Superseded by ADR-0045 (frontend Zod v4 DTOs)  
**Date**: 2025-10-21  
**Category**: data  
**Domain**: Flights DTO

## Context

Flight-related data models and flows had diverged across API, business service, and orchestration layers. Redundant DTOs (e.g., legacy domain models, API-specific models) increased cognitive load and maintenance cost. A bespoke Duffel HTTP wrapper also duplicated provider concerns while limiting evolution to additional providers.

## Decision

- Establish a single canonical set of flight domain models in `tripsage_core/models/domain/flights_canonical.py` used by API schemas, business services, and orchestration.
- Update the business `FlightService` to produce and consume only canonical DTOs, consolidating search/booking/cancellation logic behind a single boundary.
- Update the API schemas (`tripsage/api/schemas/flights.py`) to re-export canonical models and common request types, so the public API surface matches the canonical contract.
- Align the router (`tripsage/api/routers/flights.py`) to return canonical response bodies and to translate `Core*Error` exceptions into consistent HTTP errors (422 validation, 404 not found, 502 upstream failures).
- Update the TypeScript AI SDK v6 flight tools to call `FlightService` directly and format results using canonical fields.
- Remove deprecated/duplicated code:
  - Deleted legacy Duffel HTTP client and tests.
  - Removed legacy flight models and re-export shims.
  - Pruned integration tests referencing removed clients.
- Remove provider-specific DTO modules. Adapters return raw provider dicts that are converted centrally by `tripsage_core/models/mappers/flights_mapper.py` into canonical models.

## Alternatives Considered

- Maintain parallel DTOs per layer: rejected due to duplication and drift risk.
- Preserve legacy Duffel wrapper: rejected; the external API service in `services/external_apis` plus a mapper covers the need with lower bespoke code.

## Consequences

- Single source of truth for DTOs reduces duplication and test surface.
- Router and agent rely on one service boundary, simplifying evolution.
- Tests rewritten to the final contract; legacy tests and modules removed.

## Implementation Notes

- Canonical models live in `tripsage_core/models/domain/flights_canonical.py`.
- API schemas re-export canonical types for stable public shapes.
- Mapper converts Duffel offers into canonical `FlightOffer`.
- `FlightService` includes stabilization for cache keys, date normalization, and passenger counts. External adapters remain optional and are converted via the mapper.

## Rollout and Validation

- Lint/type/test gates run over the changed modules with `ruff`, `pyright`, and `pylint` clean. New deterministic unit tests cover the mapper, service booking/cancel, agent integration, and the router contract.

## Changelog

- 1.0.0 (2025-10-24) — Standardized metadata and formatting; added version and changelog.
