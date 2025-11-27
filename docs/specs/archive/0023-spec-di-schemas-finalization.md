# SPEC-0023: Final DI + Pydantic v2 Schemas Centralization (Final-Only)

Status: Superseded

Owners: Platform API

Date: 2025-10-24  
**Superseded By**: Python backend removed (see SPEC-0020)

**Superseded Note:** This spec covered Python/FastAPI backend DI and Pydantic v2 schemas. The Python FastAPI backend has been completely removed. All functionality now runs in Next.js TypeScript with Zod schemas. This spec is retained for historical reference only.

## Executive Summary

This spec concludes our "final-only" migration to FastAPI `app.state` DI and Pydantic v2 schema centralization across the API layer. We removed all competing DI patterns and centralized request/response models under `tripsage/api/schemas`. This document finalizes the remaining work: dashboard realtime models, schema audit for Pydantic v2, strict response contracts, enum normalization, OpenAPI snapshot tests, and router policy tests that prevent inline `BaseModel` definitions in routers.

Scope explicitly excludes anything already implemented and verified (memory/attachments/health/trips params centralization; dashboard router refactor; README/CHANGELOG updates; lifespan smoke; limiter signatures for memory/chat; targeted test fixes). This spec covers only the remaining work to reach "no legacy code, no back-compat, no dead code".

## Decision Framework

- Solution Leverage (35%): 0.95 — Library-first schemas and FastAPI validation enforce contracts and accurate OpenAPI.
- Application Value (30%): 0.90 — Consistent, documented API improves reliability and client integrations.
- Maintenance Load (25%): 0.90 — Centralized schemas reduce duplication and test brittleness.
- Adaptability (10%): 0.85 — Versionable schemas and snapshot tests enable controlled evolution.

Weighted score: 9.13/10. Proceed.

## Inputs and Evidence

- Code review (internal + tool-assisted) of `tripsage/api/*` confirming remaining inline models in `dashboard_realtime.py`, response_model gaps, and lingering Pydantic v1 kwargs in schemas (regex/min_items) — validated and partially fixed (see PR diff where applicable).
- Targeted pytest runs for dashboard endpoints now green after centralization and test rebaseline.
- Pydantic v2 guidance: use `pattern=` (not `regex`) and `min_length`/`max_length` for list cardinality.

## Final Plan (Phased)

### Phase A — Dashboard Realtime Centralization (Routers + Schemas)

- Files
  - Source: `tripsage/api/routers/dashboard_realtime.py`
  - Target schemas: `tripsage/api/schemas/dashboard_realtime.py`

- Tasks
  - Move router-local `RealtimeMetrics`, `AlertNotification`, `SystemEvent` into new schemas module under responses.
  - Update router to import centralized models, and add `response_model` on every endpoint:
    - `GET /dashboard/realtime/events` → `list[SystemEvent]`
    - `POST /dashboard/realtime/alerts/broadcast` → `{success: bool}` or typed `BroadcastResponse`
    - `POST /dashboard/realtime/events/broadcast` → typed `BroadcastResponse`
    - `GET /dashboard/realtime/connections` → typed `ConnectionsStatusResponse`
  - Normalize any enums to the shared dashboard enums where relevant.
  - Remove all inline `BaseModel` from the router.

- Tests
  - Update/add unit tests in `tests/unit/api/routers/test_dashboard_realtime_router.py` asserting response models and payload shapes.
  - Ensure no direct dependency on router-local models remains.

### Phase B — Schemas v2 Audit (repo-wide under `tripsage/api/schemas`)

- Files
  - All under `tripsage/api/schemas/**/*`

- Tasks
  - Replace Pydantic v1 kwargs with v2 equivalents: `regex` → `pattern`, `min_items` → `min_length` (for lists), etc.
  - Confirm validators are v2-compliant (use `@field_validator`/`@model_validator` patterns as needed).
  - Ensure request vs response split is respected; migrate any remaining router-local DTOs to requests/responses packages.
  - Add `ErrorEnvelope` and reuse for typed error responses where routers catch exceptions.

- Tests
  - `tests/unit/api/policy/test_schemas_v2.py` — quick import/smoke ensuring no v1-only kwargs appear.

### Phase C — Response Model Enforcement (All Routers)

- Files
  - Routers with gaps: `tripsage/api/routers/attachments.py` (read/list/delete/download), `search.py` (analytics), `itineraries.py` (some endpoints), `config.py` (rollback, environment), plus any others found by scan.

- Tasks
  - Add/align `response_model` on every endpoint.
  - Define missing response schemas under feature modules (e.g., `schemas/attachments.py` for `FileMetadataResponse`, `FileListResponse`, `DeleteFileResponse`).
  - Set `response_model_exclude_none=True` selectively to keep wire formats stable.
  - Ensure FastAPI `validate_response=True` for critical endpoints.

- Tests
  - Adjust existing tests expecting free-form dicts to assert typed models instead.
  - Add OpenAPI snapshot (see Phase D).

### Phase D — Contract Guardrails (Policy + OpenAPI Snapshot)

- Files
  - Policy test: `tests/unit/api/policy/test_router_schema_policy.py`
  - Snapshot: `tests/unit/api/policy/test_openapi_snapshot.py`

- Tasks
  - Router Policy: fail if any `tripsage/api/routers/*.py` declares `BaseModel` subclasses (regex or AST-based check). This enforces no inline DTOs.
  - OpenAPI snapshot: export `/openapi.json` for the app and compare against a committed golden file. Fail on breaking changes. Allow additive changes via explicit snapshot update.

### Phase E — Enum Normalization and Safety

- Files
  - `tripsage/api/routers/dashboard.py`, `keys.py`, `trips.py` (and others using enums)
  - `tripsage/api/schemas/*` enum definitions

- Tasks
  - Convert string literal returns to typed enums at the router edge.
  - Provide safe parsing from service-produced strings using `getattr(x, "value", x)` before enum construction; add sensible fallbacks.
  - Use enum comparisons in sorting and branching logic.

### Phase F — Docs + Changelog

- Files
  - README.md (already updated DI + schema policy)
  - CHANGELOG.md (append Phase A–E bullets under Refactor)
  - Developers guide: add section on "No router-local BaseModel policy" and "OpenAPI snapshot workflow".

## File → Task Mapping (Remaining Only)

- `tripsage/api/routers/dashboard_realtime.py`
  - Remove inline models; import from `schemas/responses/dashboard_realtime.py`.
  - Add `response_model` on all endpoints.

- `tripsage/api/schemas/dashboard_realtime.py` (new)
  - Define `RealtimeMetrics`, `AlertNotification`, `SystemEvent`, `BroadcastResponse`, `ConnectionsStatusResponse`.

- `tripsage/api/routers/attachments.py`
  - Add response models on `get_file_metadata`, `delete_file`, `list_user_files`, `download_file`.
  - New schemas in `schemas/responses/attachments.py` if missing.

- `tripsage/api/schemas/**/*`
  - Replace v1-only kwargs; ensure v2 validators.

- Tests under `tests/unit/api/routers/` and `tests/integration/`
  - Rebaseline to new typed responses.
  - Add policy and openapi snapshot tests.

## Quality Gates

- Activate venv: `source .venv/bin/activate`
- Format/Lint/Type:
  - `ruff format . && ruff check . --fix`
  - `uv run pyright`
  - `uv run pylint tripsage tripsage_core`
- Tests:
  - `uv run pytest --maxfail=1 -q`
  - Coverage target remains ≥90% for touched modules; openapi snapshot and policy tests included.

## Risks and Mitigations

- Test breakage from stricter response models → Rebaseline tests alongside router changes; snapshot guards to stabilize.
- Schema drift across domains → Router policy test prevents future inline DTOs; single-source schemas enforce shapes.
- Unknown enum/string values → Safe mapping with fallbacks; log and continue.

## Rollout & Cleanup

- Single PR/branch completing Phases A–E; delete all superseded router-local models immediately.
- Update CHANGELOG under Refactor:
  - "Dashboard Realtime: centralized response models; added strict response_model contracts."
  - "Pydantic v2 audit across schemas; removed v1-only kwargs."
  - "Router policy and OpenAPI snapshot tests added to enforce final-only pattern."

## Acceptance Criteria

- No inline `BaseModel` classes in any router files.
- Every endpoint declares `response_model` and returns schema-conformant data.
- OpenAPI snapshot test passes; policy test passes.
- Ruff, Pyright, Pylint clean for touched modules; pytest green for updated suites.
