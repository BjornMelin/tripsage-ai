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
| [ADR-0003](adr-0003-dragonfly-caching.md) | Use DragonflyDB for High-Performance Caching | Accepted | 2025-06-17 |
| [ADR-0004](adr-0004-fastapi-backend.md) | FastAPI as Backend Framework | Accepted | 2025-06-17 |
| [ADR-0005](adr-0005-nextjs-react19.md) | Next.js 15 with React 19 for Frontend | Accepted | 2025-06-17 |
| [ADR-0006](adr-0006-websocket-architecture.md) | Real-time Communication via WebSockets | Accepted | 2025-06-17 |
| [ADR-0007](adr-0007-testing-strategy.md) | Modern Testing Strategy with Vitest and Playwright | Accepted | 2025-06-17 |
| [ADR-0008](adr-0008-pydantic-v2-migration.md) | Migrate to Pydantic v2 | Accepted | 2025-06-17 |

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