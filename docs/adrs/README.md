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
| [ADR-0006](adr-0006-websocket-architecture.md) | Real-time Communication via WebSockets | Accepted | 2025-06-17 |
| [ADR-0007](adr-0007-testing-strategy.md) | Modern Testing Strategy with Vitest and Playwright | Accepted | 2025-06-17 |
| [ADR-0008](adr-0008-pydantic-v2-migration.md) | Migrate to Pydantic v2 | Accepted | 2025-06-17 |
| [ADR-0013](adr-0013-adopt-next-js-16-proxy-and-async-apis-deprecate-middleware.md) | Adopt Next.js 16 proxy and async APIs; deprecate middleware | Accepted | 2025-10-23 |
| [ADR-0014](adr-0014-migrate-supabase-auth-to-supabase-ssr-and-deprecate-auth-helpers-react.md) | Migrate Supabase auth to @supabase/ssr; deprecate auth-helpers-react | Accepted | 2025-10-23 |
| [ADR-0015](adr-0015-upgrade-ai-sdk-to-v5-ai-sdk-react-and-usechat-redesign.md) | Upgrade AI SDK to v5 (@ai-sdk/react) and useChat redesign | Accepted | 2025-10-23 |
| [ADR-0016](adr-0016-tailwind-css-v4-migration-css-first-config.md) | Tailwind CSS v4 migration (CSS-first config) | Accepted | 2025-10-23 |
| [ADR-0017](adr-0017-adopt-node-js-v24-lts-baseline.md) | Adopt Node.js v24 LTS baseline | Accepted | 2025-10-23 |
| [ADR-0018](adr-0018-centralize-supabase-typed-helpers-for-crud.md) | Centralize Supabase typed helpers for CRUD | Accepted | 2025-10-23 |
| [ADR-0019](adr-0019-canonicalize-chat-service-fastapi.md) | Canonicalize chat service via FastAPI backend | Accepted | 2025-10-24 |
| [ADR-0020](adr-0020-rate-limiting-strategy.md) | Rate limiting strategy (Next @upstash/ratelimit + FastAPI SlowAPI) | Accepted | 2025-10-24 |

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
