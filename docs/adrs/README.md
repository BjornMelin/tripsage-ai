# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the TripSage project. ADRs document significant architectural decisions made during the project's development.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences.

## ADR Process

1. **Proposing a new ADR**:
   - Copy `template.md` to a new file named `adr-XXXX-short-title.md`
   - Fill in all sections
   - Submit for review via pull request

2. **ADR Lifecycle**:
   - **Proposed**: Under discussion
   - **Accepted**: Decision has been made
   - **Deprecated**: No longer relevant
   - **Superseded**: Replaced by another ADR

## Decision Log

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0001](adr-0001-langgraph-orchestration.md) | Use LangGraph for Agent Orchestration | Accepted | 2025-06-17 |
| [ADR-0002](adr-0002-supabase-platform.md) | Adopt Supabase as Primary Database and Auth Platform | Accepted | 2025-06-17 |
| [ADR-0003](adr-0003-upstash-redis.md) | Use Upstash Redis (HTTP) for Caching | Accepted | 2025-10-22 |
| [ADR-0004](adr-0004-fastapi-backend.md) | FastAPI as Backend Framework | Accepted | 2025-06-17 |
| [ADR-0005](adr-0005-nextjs-react19.md) | Next.js 15 with React 19 for Frontend | Accepted | 2025-06-17 |
| [ADR-0006](adr-0006-websocket-architecture.md) | Superseded: legacy socket architecture (replaced by Supabase Realtime) | Superseded | 2025-06-17 |
| [ADR-0007](adr-0007-testing-strategy.md) | Modern Testing Strategy with Vitest and Playwright | Accepted | 2025-06-17 |
| [ADR-0008](adr-0008-pydantic-v2-migration.md) | Migrate to Pydantic v2 | Accepted | 2025-06-17 |
| [ADR-0009](adr-0009-consolidate-ci-to-two-workflows-and-remove-custom-composites.md) | Consolidate CI to two workflows and remove custom composites | Proposed | 2025-10-18 |
| [ADR-0010](adr-0010-memory-facade-final.md) | Memory Facade Final | Accepted | 2025-10-21 |
| [ADR-0011](adr-0011-tenacity-only-resilience.md) | Tenacity-only Resilience | Accepted | 2025-10-21 |
| [ADR-0012](adr-0012-flights-canonical-dto.md) | Flights Canonical DTO | Accepted | 2025-10-21 |
| [ADR-0013](adr-0013-adopt-next-js-16-proxy-and-async-apis-deprecate-middleware.md) | Adopt Next.js 16 proxy and async APIs; deprecate middleware | Accepted | 2025-10-23 |
| [ADR-0014](adr-0014-migrate-supabase-auth-to-supabase-ssr-and-deprecate-auth-helpers-react.md) | Migrate Supabase auth to @supabase/ssr; deprecate auth-helpers-react | Accepted | 2025-10-23 |
| [ADR-0015](adr-0015-upgrade-ai-sdk-to-v5-ai-sdk-react-and-usechat-redesign.md) | Upgrade AI SDK to v5 (@ai-sdk/react) and useChat redesign | Accepted | 2025-10-23 |
| [ADR-0016](adr-0016-tailwind-css-v4-migration-css-first-config.md) | Tailwind CSS v4 migration (CSS-first config) | Accepted | 2025-10-23 |
| [ADR-0017](adr-0017-adopt-node-js-v24-lts-baseline.md) | Adopt Node.js v24 LTS baseline | Accepted | 2025-10-23 |
| [ADR-0018](adr-0018-centralize-supabase-typed-helpers-for-crud.md) | Centralize Supabase typed helpers for CRUD | Accepted | 2025-10-23 |
| [ADR-0019](adr-0019-canonicalize-chat-service-fastapi.md) | Canonicalize chat service via FastAPI backend | Accepted | 2025-10-24 |
| [ADR-0020](adr-0020-rate-limiting-strategy.md) | Rate limiting strategy (Next @upstash/ratelimit + FastAPI SlowAPI) | Accepted | 2025-10-24 |
| [ADR-0021](adr-0021-slowapi-aiolimiter-migration-historic.md) | SlowAPI + Aiolimiter Migration (Historic) | Deprecated | 2025-10-24 |
| [ADR-0022](adr-0022-python-pytest-foundation.md) | Standardize Python Test Suite Foundations | Accepted | 2025-10-24 |
| [ADR-0023](adr-0023-adopt-ai-sdk-v6-foundations.md) | Adopt AI SDK v6 Foundations (Next.js App Router) | Accepted | 2025-11-01 |
| [ADR-0024](adr-0024-byok-routes-and-security.md) | BYOK Routes and Security (Next.js + Supabase Vault) | Accepted | 2025-11-01 |
| [ADR-0026](adr-0026-adopt-ai-elements-ui-chat.md) | Adopt AI Elements UI Chat | Accepted | 2025-11-01 |
| [ADR-0027](adr-027-token-budgeting-and-limits.md) | Token Budgeting & Limits (Counting + Clamping) | Accepted | 2025-11-01 |
| [ADR-0028](adr-0028-provider-registry.md) | Provider Registry & Resolution | Accepted | 2025-11-01 |
| [ADR-0029](adr-0029-di-route-handlers-and-testing.md) | DI Route Handlers and Testing | Accepted | 2025-11-02 |
| [ADR-0031](adr-0031-nextjs-chat-api-ai-sdk-v6.md) | Next.js Chat API AI SDK v6 | Accepted | 2025-11-02 |
| [ADR-0032](adr-0032-centralized-rate-limiting.md) | Centralized Rate Limiting | Accepted | 2025-11-02 |
| [ADR-0033](adr-0033-rag-advanced-v6.md) | RAG Advanced v6 | Proposed | 2025-11-02 |
| [ADR-0034](adr-0034-structured-outputs-object-generation.md) | Structured Outputs Object Generation | Accepted | 2025-11-02 |

## By Category

### Frontend

- ADR-0005: Next.js 15 with React 19 for Frontend
- ADR-0013: Adopt Next.js 16 proxy and async APIs; deprecate middleware
- ADR-0014: Migrate Supabase auth to @supabase/ssr; deprecate auth-helpers-react
- ADR-0015: Upgrade AI SDK to v5 (@ai-sdk/react) and useChat redesign
- ADR-0016: Tailwind CSS v4 migration (CSS-first config)
- ADR-0018: Centralize Supabase typed helpers for CRUD
- ADR-0023: Adopt AI SDK v6 Foundations (Next.js App Router)
- ADR-0026: Adopt AI Elements UI Chat
- ADR-0027: Token Budgeting & Limits (Counting + Clamping)
- ADR-0028: Provider Registry & Resolution
- ADR-0029: DI Route Handlers and Testing
- ADR-0031: Next.js Chat API AI SDK v6
- ADR-0034: Structured Outputs Object Generation

### Backend

- ADR-0001: Use LangGraph for Agent Orchestration
- ADR-0004: FastAPI as Backend Framework
- ADR-0010: Memory Facade Final
- ADR-0011: Tenacity-only Resilience
- ADR-0019: Canonicalize chat service via FastAPI backend
- ADR-0021: SlowAPI + Aiolimiter Migration (Historic)

### Platform

- ADR-0002: Adopt Supabase as Primary Database and Auth Platform
- ADR-0017: Adopt Node.js v24 LTS baseline

### Security

- ADR-0020: Rate limiting strategy (Next @upstash/ratelimit + FastAPI SlowAPI)
- ADR-0024: BYOK Routes and Security (Next.js + Supabase Vault)
- ADR-0032: Centralized Rate Limiting

### Data

- ADR-0012: Flights Canonical DTO

### Ops

- ADR-0003: Use Upstash Redis (HTTP) for Caching
- ADR-0007: Modern Testing Strategy with Vitest and Playwright
- ADR-0009: Consolidate CI to two workflows and remove custom composites
- ADR-0022: Standardize Python Test Suite Foundations

## Creating a New ADR

When creating a new ADR:

1. Use the next available number (e.g., if the last ADR is 0008, use 0009)
2. Follow the naming convention: `adr-XXXX-short-title.md`
3. Keep the title descriptive but concise
4. Link related ADRs in the references section
5. Update this README with the new entry

## Tools and References

- [ADR Tools](https://github.com/npryce/adr-tools) - Command-line tools for working with ADRs
- [Michael Nygard's ADR template](https://github.com/joelparkerhenderson/architecture-decision-record/blob/main/templates/decision-record-template-by-michael-nygard/index.md)
- [ADR GitHub](https://adr.github.io/) - Architectural Decision Records resources
