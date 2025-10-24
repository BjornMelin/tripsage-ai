# ADR-0010: Final Memory Facade with LangGraph Alignment

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-10-21

## Context

The repository contained multiple memory entry points: a legacy `tripsage/tools/memory_tools.py` using a non-standard tool context and MCP mocks in `orchestration/tools/tools.py`. These caused drift from the `MemoryService` contract and prevented consistent LangGraph usage, observability, and testing.

## Decision

Adopt a single, final implementation:

- Replace `tripsage/tools/memory_tools.py` with LangGraph-aligned, library-first functions that directly use `tripsage_core.services.business.memory_service` request models.
- Remove intermediate adapters and MCP-based fallbacks for memory operations.
- Provide OpenTelemetry tracing and histograms via `tripsage_core/observability/otel.py` for all public memory functions.
- Update `orchestration/tools/tools.py` to call the new memory functions, ensuring one authoritative code path.
- Delete superseded code paths as part of the change.

## Consequences

- Fewer moving parts, lower maintenance risk, and contract enforcement via strict Pydantic models.
- LangGraph agents now share a consistent memory backend with traceable spans and metrics.
- Testability improves: unit tests can monkeypatch `get_memory_service()` and assert behavior deterministically.

## Migration

- No back-compat layer is retained. MCP memory stubs are removed for add/search routes.
- Existing callers importing `ConversationMessage` continue to work; the type re-exports from `tripsage.tools.models`.

## Alternatives Considered

- Transitional thin adapters first, façade later. Rejected to satisfy FINAL-ONLY directive and reduce code churn.

## Changelog

- 1.0.0 (2025-10-24) — Standardized metadata and formatting; added version and changelog.
