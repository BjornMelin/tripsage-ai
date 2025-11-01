# ADR-0022: Standardize Python Test Suite Foundations

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-10-24
**Category**: ops
**Domain**: Backend Testing

## Context

The Python `tests/` tree accumulated large, inconsistent suites over multiple migrations (Supabase, FastAPI, Realtime). Many files still rely on legacy patterns:

- Blocking sleeps, manual benchmark loops, and heavyweight mocks instead of deterministic async tests.
- Multiple `conftest.py` variants with divergent fixtures and conflicting state.
- Real Redis or Supabase dependencies required for “integration” suites, leading to brittle pipelines.
- Lack of canonical data factories; fixtures duplicate hard-coded payloads across directories.

Recent research (pytest-asyncio loop scopes, fakeredis async clients, Polyfactory pytest integration, httpx ASGI transport) and Spec 0010 mandate a unified approach so that the refactor effort does not drift from best practices.

## Decision

We adopt the following foundations for all Python test suites:

1. **Directory & Marker Canon** — Enforce the layout `tests/{unit,integration,e2e,performance,security,docker}` with shared `tests/fixtures` and `tests/factories`. Root `pytest.ini` declares markers for each suite plus `perf`, `slow`, and `timeout`, and sets `asyncio_mode = strict`.
2. **Async-First Pytest** — All async tests and fixtures use `pytest-asyncio`, leveraging `loop_scope` to avoid event-loop reuse bugs. Blocking sleeps and benchmark plugins are removed in favor of deterministic assertions plus `pytest.mark.timeout`.
3. **Deterministic Infra Mocks** — Cache-dependent code uses `fakeredis.FakeAsyncRedis`; FastAPI flows rely on `httpx.ASGITransport(app=create_app())`-backed `AsyncClient` fixtures. Database fixtures prefer lightweight SQLite/asyncpg configurations rather than full Supabase.
4. **Generated Test Data** — Domain objects are produced via Polyfactory-registered pytest fixtures (e.g., API keys, trips, accommodations) instead of hand-crafted dicts, ensuring consistency with Pydantic models.
5. **Quality Gates** — Ruff format/check and Pyright strict mode run against `tests/`. Pytest executions (`uv run pytest --maxfail=1 --durations=10`) must complete in under 60 seconds with ≥90% backend coverage.

These requirements are codified in Spec 0010 and must be satisfied before any refactored test suite is considered complete.

## Consequences

### Positive

- Predictable, async-safe fixtures that work locally and in CI.
- Reduced flakiness from external dependencies; faster feedback for developers.
- Shared factories eliminate duplicated payload builders and improve coverage confidence.
- Clear marker taxonomy enables selective running (e.g., `-m "not performance"`).

### Negative

- Initial rewrite cost: large suites need to be split or removed, and engineers must learn Polyfactory/fakeredis idioms.
- Additional dev dependencies (`fakeredis`, `polyfactory`, pytest plugins) require maintenance and version tracking.

### Neutral

- Integration tests still validate real HTTP flows via ASGI transport; switching to real services remains an option for specific cases but is no longer the default.

## Alternatives Considered

### Keep Legacy Fixtures and Benchmarks

Rejected: preserves flaky suites, duplicates infra state, and blocks strict async execution.

### Rely on Real Redis/Supabase for All Integration Tests

Rejected: increases CI cost and brittleness; fakeredis + focused DB fixtures provide sufficient confidence for most cases while keeping runs fast.

### Use Factory Boy Instead of Polyfactory

Rejected: Polyfactory natively understands Pydantic v2 and integrates with pytest fixtures with less boilerplate.

## References

- Spec 0010 — Python Test Suite Modernization
- ADR-0004 — FastAPI as Backend Framework
- ADR-0007 — Modern Testing Strategy with Vitest and Playwright
- fakeredis documentation (<https://fakeredis.readthedocs.io>)
- polyfactory pytest plugin (<https://polyfactory.litestar.dev/latest/usage/fixtures.html>)
- httpx ASGI transport docs (<https://www.python-httpx.org/advanced/transports/>)
