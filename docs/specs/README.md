# Technical Specifications

This directory contains Technical Specifications (Specs) for the TripSage
project. Specs document detailed technical requirements, API contracts, and
implementation guidelines for specific features and components.

## What is a Spec?

A Technical Specification (Spec) is a document that provides detailed technical
requirements, API contracts, implementation details, and testing guidelines for
specific features or components.

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

## Directory Layout

- `active/` — Draft, proposed, or in-progress specifications.
- `archive/` — Completed, accepted, implemented, or superseded specifications (including migrations).

## Active Specifications

| Spec | Title | Status | Date |
|------|-------|--------|------|
| [SPEC-0017](active/0017-spec-attachments-migration-next.md) | Attachments & File Uploads Migration (Next.js) | Partial | 2025-11-04 |
| [SPEC-0018](active/0018-spec-rag-retriever-indexer.md) | RAG Retriever & Indexer (AI SDK v6) | Partial | 2025-11-04 |
| [SPEC-0021](active/0021-spec-supabase-webhooks-vercel-consolidation.md) | Supabase Webhooks to Vercel Consolidation | Draft | 2025-11-12 |
| [SPEC-0032](active/0032-spec-upstash-testing-harness.md) | Upstash Testing Harness (Mocks, Emulators, Smoke) | Proposed | 2025-11-24 |

## Archived Specifications

Completed, accepted, implemented, and superseded specs (plus historical migrations) are stored in [`archive/`](archive/). Refer to individual files there for status history and outcomes.

## Creating a New Spec

When creating a new spec:

1. Use the next available number (e.g., if the last spec is 0018, use 0019)
2. Follow the naming convention: `XXXX-spec-short-title.md`
3. Include status, date, and other relevant metadata
4. Link related ADRs and specs in the references section
5. Update this README with the new entry

## Tools and References

- [ADR Documentation](../architecture/decisions/README.md) - Related architectural decisions
- [Project Architecture](../architecture/) - Overall system architecture
