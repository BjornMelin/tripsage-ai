# Technical Specifications

This directory contains Technical Specifications (Specs) for the TripSage project. Specs document detailed technical requirements, API contracts, and implementation guidelines for specific features and components.

## What is a Spec?

A Technical Specification (Spec) is a document that provides detailed technical requirements, API contracts, implementation details, and testing guidelines for specific features or components.

## Spec Process

1. **Proposing a new spec**:
   - Create a new file named `XXXX-spec-short-title.md`
   - Fill in the required sections
   - Submit for review via pull request

2. **Spec Lifecycle**:
   - **Draft**: Under development or review
   - **Accepted**: Approved for implementation
   - **Completed**: Successfully implemented
   - **Superseded**: Replaced by another spec

## Specification Log

| Spec | Title | Status | Date |
|------|-------|--------|------|
| [SPEC-0001](0001-spec-ai-sdk-v5.md) | AI SDK v5 Migration (Client + Route) | Superseded by ADR-0031 | 2025-10-24 |
| [SPEC-0002](0002-spec-next16-migration.md) | Next.js 16 Migration (Proxy, Async APIs, Turbopack) | Accepted | 2025-10-24 |
| [SPEC-0003](0003-spec-session-resume.md) | Session Resume — TripSage Frontend | Accepted | 2025-10-24 |
| [SPEC-0004](0004-spec-supabase-ssr-typing.md) | Supabase SSR Typing Migration | Accepted | 2025-10-24 |
| [SPEC-0005](0005-spec-tailwind-v4.md) | Tailwind CSS v4 Migration | Completed | 2025-10-23 |
| [SPEC-0006](0006-spec-zod-v4-migration.md) | Zod v3 -> v4 Migration | Completed | 2025-10-23 |
| [SPEC-0007](0007-di-schemas-finalization.md) | Final DI + Pydantic v2 Schemas Centralization | Accepted | 2025-10-24 |
| [SPEC-0007](0007-spec-sse-chat-streaming.md) | SSE Chat Streaming (End-to-End) | Accepted | 2025-10-24 |
| [SPEC-0008](0008-spec-ai-sdk-v6-foundations.md) | AI SDK v6 Foundations (Next.js) | Draft | 2025-11-04 |
| [SPEC-0008](0008-spec-rate-limiting.md) | Rate Limiting Strategy | Accepted | 2025-10-24 |
| [SPEC-0009](0009-spec-attachments-ssr-listing-and-cache-tags.md) | Attachments SSR Listing and Cache Tags | Accepted | 2025-10-24 |
| [SPEC-0010](0010-spec-ai-elements-chat-ui.md) | AI Elements Chat UI | Accepted | 2025-11-01 |
| [SPEC-0010](0010-spec-python-test-suite-modernization.md) | Python Test Suite Modernization | Draft | 2025-10-24 |
| [SPEC-0011](0011-spec-byok-routes-and-security.md) | BYOK Routes and Security (Next.js + Supabase Vault) | Accepted | 2025-11-01 |
| [SPEC-0012](0012-provider-registry.md) | Provider Registry | Accepted | 2025-11-01 |
| [SPEC-0013](0013-token-budgeting-and-limits.md) | Token Budgeting & Limits | Accepted | 2025-11-01 |
| [SPEC-0014](0014-spec-chat-api-sse-nonstream.md) | Chat API (SSE + Non-Stream) | Draft | 2025-11-04 |
| [SPEC-0015](0015-spec-ai-elements-response-sources.md) | AI Elements Response + Sources Integration | Accepted | 2025-11-04 |
| [SPEC-0016](0016-spec-react-compiler-enable.md) | Enable React Compiler in Next.js 16 | Accepted | 2025-11-04 |
| [SPEC-0017](0017-spec-attachments-migration-next.md) | Attachments & File Uploads Migration (Next.js) | Draft | 2025-11-04 |
| [SPEC-0018](0018-spec-rag-retriever-indexer.md) | RAG Retriever & Indexer (AI SDK v6) | Draft | 2025-11-04 |

## By Category

### Frontend

- SPEC-0002: Next.js 16 Migration (Proxy, Async APIs, Turbopack)
- SPEC-0003: Session Resume — TripSage Frontend
- SPEC-0004: Supabase SSR Typing Migration
- SPEC-0005: Tailwind CSS v4 Migration
- SPEC-0006: Zod v3 -> v4 Migration
- SPEC-0008: AI SDK v6 Foundations (Next.js)
- SPEC-0010: AI Elements Chat UI
- SPEC-0012: Provider Registry
- SPEC-0013: Token Budgeting & Limits
- SPEC-0014: Chat API (SSE + Non-Stream)
- SPEC-0015: AI Elements Response + Sources Integration
- SPEC-0016: Enable React Compiler in Next.js 16
- SPEC-0017: Attachments & File Uploads Migration (Next.js)

### Backend

- SPEC-0001: AI SDK v5 Migration (Client + Route)
- SPEC-0007: Final DI + Pydantic v2 Schemas Centralization
- SPEC-0007: SSE Chat Streaming (End-to-End)
- SPEC-0008: Rate Limiting Strategy
- SPEC-0009: Attachments SSR Listing and Cache Tags
- SPEC-0010: Python Test Suite Modernization
- SPEC-0011: BYOK Routes and Security (Next.js + Supabase Vault)
- SPEC-0018: RAG Retriever & Indexer (AI SDK v6)

## Creating a New Spec

When creating a new spec:

1. Use the next available number (e.g., if the last spec is 0018, use 0019)
2. Follow the naming convention: `XXXX-spec-short-title.md`
3. Include status, date, and other relevant metadata
4. Link related ADRs and specs in the references section
5. Update this README with the new entry

## Tools and References

- [ADR Documentation](../adrs/README.md) - Related architectural decisions
- [Project Architecture](../../docs/architecture/) - Overall system architecture
