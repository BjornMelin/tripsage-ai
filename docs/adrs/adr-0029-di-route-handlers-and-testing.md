# ADR-0029: DI Handlers + Thin Adapters for Next.js App Router API Testing

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-02
**Category**: Architecture
**Domain**: Frontend API (App Router)
**Related ADRs**: ADR-0028, ADR-0026
**Related Specs**: specs/0013-token-budgeting-and-limits.md

## Context

Our App Router API routes depend on SSR auth (Supabase), rate limiting (Upstash), and AI SDK v6 streaming. Directly testing route modules caused hanging Vitest workers due to:

- Module-scope side effects (Upstash clients at import-time based on env)
- Streaming bodies left open when tests don't consume toUIMessageStreamResponse
- SSR-only constructs (cookies/headers) mixed into unit tests

We need a stable, industry-aligned approach to make routes testable, deterministic, and maintainable.

## Decision

We will:

- Adopt Dependency Injection (DI) for route logic:
  - Extract business logic into _handler.ts files that accept collaborators (supabase, resolveProvider, optional limit, logger, clock, config)
  - For streaming, accept an optional stream?: typeof streamText to inject a finite stub in tests
- Keep route.ts thin (adapter-only):
  - Parse NextRequest
  - Build SSR-only clients (Supabase) and lazy, cached Upstash Ratelimit inside POST (not at module-scope)
  - Call the DI handler and return its Response
- Testing strategy:
  - Prefer deterministic unit tests for handlers with fakes/stubs
  - Keep 1–2 adapter smoke tests per route (401/429) using vi.resetModules + vi.stubEnv before import; mock Upstash and SSR clients; avoid actual streaming paths
  - Use Node test environment for API suites

## Consequences

### Positive

- Deterministic and fast tests (no open handles or network side effects)
- Clear separation of concerns (SSR-only adapters vs. pure handlers)
- Easier evolution (new providers/tools via DI)

### Negative

- Minor refactor overhead to introduce DI seams
- Slight complexity to maintain collaborators across handler boundaries

### Neutral

- Adapter smokes remain minimal; most coverage shifts to handlers

## Alternatives Considered

### Test routes directly with heavy mocks

- Rejected: brittle and still prone to module-scope env and streaming hangs; higher maintenance.

### MSW-based full integration

- Rejected for unit scope: heavier infra; slower; still requires careful env/mocks; better for higher-level tests.

## References

- Next.js + Vitest testing guide: <https://nextjs.org/docs/app/guides/testing/vitest>
- Clean Architecture, thin controllers/adapters patterns (multiple sources)
- AI SDK v6 testing: simulateReadableStream and UI message stream response helpers (ai-sdk.dev)
