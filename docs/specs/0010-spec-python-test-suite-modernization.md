# Spec: Python Test Suite Modernization

**Status**: Draft
**Version**: 1.0.0
**Date**: 2025-10-24

## Objective

Modernize and reorganize the Python `tests/` hierarchy to align with the 2025 pytest strategy: deterministic async-first coverage, fast feedback, and maintainable fixtures that reflect the canonical FastAPI/tripsage_core APIs.

## Scope

- Applies to all Python test suites under `tests/` (unit, integration, e2e, performance, security, docker, shared fixtures, root helpers).
- Covers pytest configuration, directory layout, fixture strategy, data factories, async client usage, and performance guards.
- Excludes frontend Vitest/Playwright configuration (covered by ADR-0007) and CI orchestration mechanics (covered by ADR-0009).

## Implementation Checklist

- [ ] Replace ad-hoc directory sprawl with canonical layout:
  - `tests/unit/**`, `tests/integration/**`, `tests/e2e/**`, `tests/performance/**`, `tests/security/**`, `tests/docker/**`, `tests/fixtures/**`, `tests/factories/**`, plus root helpers.
  - Remove duplicate `conftest.py` variants; consolidate shared fixtures per scope.
- [ ] Add/update `pytest.ini` markers to include `unit`, `integration`, `e2e`, `performance`, `security`, `docker`, `slow`, `perf`, `timeout`, and enforce `asyncio_mode = strict`.
- [ ] Standardize async testing with `pytest-asyncio`:
  - Apply `@pytest.mark.asyncio` or async fixtures per test module.
  - Use fixture `loop_scope`/`scope` combinations to prevent event-loop drift (session-level caches, module-level clients, function-level isolation).
- [ ] Provide canonical service fixtures:
  - `fakeredis.FakeAsyncRedis` for cache-dependent code paths.
  - `httpx.ASGITransport(app=create_app())`-backed `AsyncClient` fixtures for FastAPI integration/e2e flows.
  - Database fixtures relying on lightweight SQLite/asyncpg test engines without full Supabase bootstrap.
- [ ] Register Polyfactory-backed factories as pytest fixtures for domain models (API keys, trips, accommodations, chat messages) to avoid hand-written object builders.
- [ ] Ensure root `tests/conftest.py` exposes shared pytest plugins (markers, fakeredis, polyfactory, monkeypatch helpers) without side effects.
- [ ] Cull or rewrite oversized legacy suites (e.g., `test_api_key_performance.py`) to match modern patterns; remove any reliance on sleeps, threads, or benchmark plugins.
- [ ] Add coverage guards and quality gates:
  - Enforce Ruff formatting/checking and Pyright strict mode for `tests/` via pre-commit or CI.
  - Document minimum backend test coverage (≥90%) and ensure `uv run pytest --maxfail=1 --durations=10` stays under 60s locally.
- [ ] Document fixture usage and directory conventions in `docs/developers/testing-python.md` (or nearest developer guide).

## Acceptance Criteria

- Running `uv run ruff format tests` and `uv run ruff check tests` produces no changes/diagnostics.
- `uv run pyright` passes with zero errors, including test modules.
- `uv run pytest` completes in under 60 seconds on a developer machine with ≥90% coverage (backend) and markers respected.
- No legacy benchmark/sleep-based performance suites remain; all performance checks rely on markers + timeout assertions.
- Shared fixtures leverage fakeredis + Polyfactory patterns; integration/e2e suites exclusively use ASGI transport-backed clients.
- Directory structure and markers align with this spec and are enforced in documentation.

## References

- ADR-0007: Modern Testing Strategy with Vitest and Playwright
- ADR-0004: FastAPI as Backend Framework
- ExecPlan: `.agent/execplans/tests_refactor.md`
- Research notes: pytest-asyncio fixture guidance, fakeredis docs, Polyfactory pytest plugin, httpx ASGI transport usage
