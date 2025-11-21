# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the TripSage
project. ADRs document significant architectural decisions made during the
project's development.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important
architectural decision made along with its context and consequences.

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
| [ADR-0002](adr-0002-supabase-platform.md) | Adopt Supabase as Primary Database and Auth Platform | Accepted | 2025-06-17 |
| [ADR-0003](adr-0003-upstash-redis.md) | Use Upstash Redis (HTTP) for Caching | Accepted | 2025-10-22 |
| [ADR-0007](adr-0007-testing-strategy.md) | Modern Testing Strategy with Vitest and Playwright | Accepted | 2025-06-17 |
| [ADR-0009](adr-0009-consolidate-ci-to-two-workflows-and-remove-custom-composites.md) | Consolidate CI to two workflows and remove custom composites | Proposed | 2025-10-18 |
| [ADR-0013](adr-0013-adopt-next-js-16-proxy-and-async-apis-deprecate-middleware.md) | Adopt Next.js 16 proxy and async APIs; deprecate middleware | Accepted | 2025-10-23 |
| [ADR-0014](adr-0014-migrate-supabase-auth-to-supabase-ssr-and-deprecate-auth-helpers-react.md) | Migrate Supabase auth to @supabase/ssr; deprecate auth-helpers-react | Accepted | 2025-10-23 |
| [ADR-0016](adr-0016-tailwind-css-v4-migration-css-first-config.md) | Tailwind CSS v4 migration (CSS-first config) | Accepted | 2025-10-23 |
| [ADR-0017](adr-0017-adopt-node-js-v24-lts-baseline.md) | Adopt Node.js v24 LTS baseline | Accepted | 2025-10-23 |
| [ADR-0018](adr-0018-centralize-supabase-typed-helpers-for-crud.md) | Centralize Supabase typed helpers for CRUD | Accepted | 2025-10-23 |
| [ADR-0023](adr-0023-adopt-ai-sdk-v6-foundations.md) | Adopt AI SDK v6 Foundations (Next.js App Router) | Accepted | 2025-11-01 |
| [ADR-0024](adr-0024-byok-routes-and-security.md) | BYOK Routes and Security (Next.js + Supabase Vault) | Accepted | 2025-11-01 |
| [ADR-0026](adr-0026-adopt-ai-elements-ui-chat.md) | Adopt AI Elements UI Chat | Accepted | 2025-11-01 |
| [ADR-027](adr-027-token-budgeting-and-limits.md) | Token Budgeting & Limits (Counting + Clamping) | Accepted | 2025-11-01 |
| [ADR-0028](adr-0028-provider-registry.md) | Provider Registry & Resolution | Accepted | 2025-11-01 |
| [ADR-0029](adr-0029-di-route-handlers-and-testing.md) | DI Route Handlers and Testing | Accepted | 2025-11-02 |
| [ADR-0031](adr-0031-nextjs-chat-api-ai-sdk-v6.md) | Next.js Chat API AI SDK v6 | Accepted | 2025-11-02 |
| [ADR-0032](adr-0032-centralized-rate-limiting.md) | Centralized Rate Limiting | Accepted | 2025-11-02 |
| [ADR-0033](adr-0033-rag-advanced-v6.md) | RAG Advanced v6 | Proposed | 2025-11-02 |
| [ADR-0034](adr-0034-structured-outputs-object-generation.md) | Structured Outputs Object Generation | Accepted | 2025-11-02 |
| [ADR-0035](adr-0035-react-compiler-and-component-declarations.md) | React Compiler and Component Declarations | Accepted | 2025-11-04 |
| [ADR-0036](adr-0036-ai-elements-response-and-sources.md) | AI Elements Response and Sources | Accepted | 2025-11-04 |
| [ADR-0037](adr-0037-reasoning-tool-codeblock-phased-adoption.md) | Reasoning/Tool/CodeBlock Phased Adoption | Accepted | 2025-11-04 |
| [ADR-0038](adr-0038-hybrid-frontend-agents.md) | Frontend Hybrid Agents for Destination Research & Itineraries | Accepted | 2025-11-12 |
| [ADR-0039](adr-0039-frontend-agent-modernization.md) | Framework-First Frontend Agent Modernization | Accepted | 2025-11-12 |
| [ADR-0040](adr-0040-consolidate-supabase-edge-to-vercel-webhooks.md) | Consolidate Supabase Edge (Deno) to Vercel Route Handlers + Database Webhooks | Accepted | 2025-11-13 |
| [ADR-0041](adr-0041-webhook-notifications-qstash-and-resend.md) | Webhook Notifications via QStash and Resend | Accepted | 2025-11-13 |
| [ADR-0042](adr-0042-supabase-memory-orchestrator.md) | Supabase-Centric Memory Orchestrator | Accepted | 2025-11-18 |
| [ADR-0043](superseded/adr-0043-expedia-rapid-integration.md) | Expedia Rapid API Integration for Lodging Search/Booking | Superseded | 2025-11-19 |
| [ADR-0050](adr-0050-amadeus-google-places-stripe-hybrid.md) | Replace Expedia Rapid with Amadeus + Google Places + Stripe | Accepted | 2025-11-20 |
| [ADR-0044](adr-0044-tool-registry-ts.md) | AI SDK v6 Tool Registry and MCP Integration | Accepted | 2025-11-11 |
| [ADR-0045](adr-0045-flights-dto-frontend-zod.md) | Flights DTOs in Frontend (Next.js 16 + Zod v4) | Accepted | 2025-11-20 |
| [ADR-0046](adr-0046-otel-tracing-frontend.md) | OTEL Tracing for Next.js 16 Route Handlers | Proposed | 2025-11-20 |
| [ADR-0047](adr-0047-runtime-policy-edge-vs-node.md) | Runtime Policy for AI SDK Routes (Edge vs Node) | Proposed | 2025-11-20 |
| [ADR-0048](adr-0048-qstash-retries-and-idempotency.md) | QStash Retries and Idempotency for Webhooks/Tasks | Proposed | 2025-11-20 |

## Superseded ADRs

The following ADRs have been superseded by newer decisions:

| ADR | Title | Superseded By | Date |
|-----|-------|---------------|------|
| [ADR-0001](superseded/adr-0001-langgraph-orchestration.md) | Use LangGraph for Agent Orchestration | - | 2025-06-17 |
| [ADR-0004](superseded/adr-0004-fastapi-backend.md) | FastAPI as Backend Framework | ADR-0013 / ADR-0023 | 2025-06-17 |
| [ADR-0005](superseded/adr-0005-nextjs-react19.md) | Next.js 15 with React 19 for Frontend | ADR-0013 | 2025-06-17 |
| [ADR-0006](superseded/adr-0006-websocket-architecture.md) | Legacy WebSocket architecture (replaced by Supabase Realtime) | - | 2025-06-17 |
| [ADR-0008](superseded/adr-0008-pydantic-v2-migration.md) | Migrate to Pydantic v2 | ADR-0023 | 2025-06-17 |
| [ADR-0010](superseded/adr-0010-memory-facade-final.md) | Memory Facade Final | - | 2025-10-21 |
| [ADR-0011](superseded/adr-0011-tenacity-only-resilience.md) | Tenacity-only Resilience | ADR-0032 | 2025-10-21 |
| [ADR-0015](superseded/adr-0015-upgrade-ai-sdk-to-v5-ai-sdk-react-and-usechat-redesign.md) | Upgrade AI SDK to v5 (@ai-sdk/react) and useChat redesign | ADR-0023 | 2025-10-23 |
| [ADR-0012](superseded/adr-0012-flights-canonical-dto.md) | Canonical Flights DTOs (Python) | ADR-0045 | 2025-10-21 |
| [ADR-0019](superseded/adr-0019-canonicalize-chat-service-fastapi.md) | Canonicalize chat service via FastAPI backend | ADR-0031 | 2025-10-24 |
| [ADR-0020](superseded/adr-0020-rate-limiting-strategy.md) | Rate limiting strategy (Next + SlowAPI) | ADR-0032 | 2025-10-24 |
| [ADR-0021](superseded/adr-0021-slowapi-aiolimiter-migration-historic.md) | SlowAPI + Aiolimiter Migration (Historic) | - | 2025-10-24 |
| [ADR-0022](superseded/adr-0022-python-pytest-foundation.md) | Standardize Python Test Suite Foundations | ADR-0007 | 2025-10-24 |
| [ADR-0043](superseded/adr-0043-expedia-rapid-integration.md) | Expedia Rapid API Integration for Lodging Search/Booking | ADR-0050 | 2025-11-20 |
| [ADR-0049](superseded/adr-0049-expedia-rapid.md) | Expedia Rapid Integration Research | ADR-0050 | 2025-11-20 |

## By Category

### Frontend

- ADR-0013: Adopt Next.js 16 proxy and async APIs; deprecate middleware
- ADR-0014: Migrate Supabase auth to @supabase/ssr; deprecate auth-helpers-react
- ADR-0016: Tailwind CSS v4 migration (CSS-first config)
- ADR-0018: Centralize Supabase typed helpers for CRUD
- ADR-0023: Adopt AI SDK v6 Foundations (Next.js App Router)
- ADR-0026: Adopt AI Elements UI Chat
- ADR-027: Token Budgeting & Limits (Counting + Clamping)
- ADR-0028: Provider Registry & Resolution
- ADR-0029: DI Route Handlers and Testing
- ADR-0031: Next.js Chat API AI SDK v6
- ADR-0034: Structured Outputs Object Generation
- ADR-0035: React Compiler and Component Declarations
- ADR-0036: AI Elements Response and Sources
- ADR-0037: Reasoning/Tool/CodeBlock Phased Adoption
- ADR-0038: Frontend Hybrid Agents for Destination Research & Itineraries
- ADR-0039: Framework-First Frontend Agent Modernization
- ADR-0042: Supabase-Centric Memory Orchestrator
- ADR-0044: AI SDK v6 Tool Registry and MCP Integration
- ADR-0045: Flights DTOs in Frontend (Next.js 16 + Zod v4)

### Backend

- ADR-0040: Consolidate Supabase Edge (Deno) to Vercel Route Handlers + Database Webhooks
- ADR-0041: Webhook Notifications via QStash and Resend

### Platform

- ADR-0002: Adopt Supabase as Primary Database and Auth Platform
- ADR-0017: Adopt Node.js v24 LTS baseline
- ADR-0032: Centralized Rate Limiting
- ADR-0040: Consolidate Supabase Edge (Deno) to Vercel Route Handlers + Database Webhooks
- ADR-0041: Webhook Notifications via QStash and Resend
- ADR-0047: Runtime Policy for AI SDK Routes (Edge vs Node)
- ADR-0046: OTEL Tracing for Next.js 16 Route Handlers

### Security

- ADR-0024: BYOK Routes and Security (Next.js + Supabase Vault)
- ADR-0032: Centralized Rate Limiting
- ADR-0048: QStash Retries and Idempotency for Webhooks/Tasks

### Data

- ADR-0012: Flights Canonical DTO
- ADR-0042: Supabase-Centric Memory Orchestrator

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
