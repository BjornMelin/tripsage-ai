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

- `active/` — Current baseline specifications.
- `archive/` — Historical, completed, accepted, implemented, or superseded specifications (including migrations).

## Active Specifications

| Spec | Title | Status | Date |
| :--- | :--- | :--- | :--- |
| [SPEC-0100](active/0100-spec-application-architecture.md) | Application architecture (Next.js RSC + TanStack Query) | Final | 2026-01-05 |
| [SPEC-0101](active/0101-spec-auth-and-session.md) | Auth and session | Final | 2026-01-05 |
| [SPEC-0102](active/0102-spec-trips-domain.md) | Trips domain | Final | 2026-01-05 |
| [SPEC-0103](active/0103-spec-chat-and-agents.md) | Chat and agents (AI SDK v6) | Final | 2026-01-05 |
| [SPEC-0104](active/0104-spec-memory-and-rag.md) | Memory and RAG | Final | 2026-01-05 |
| [SPEC-0105](active/0105-spec-attachments.md) | Attachments (Supabase Storage + ingestion pipeline) | Final | 2026-01-05 |
| [SPEC-0106](active/0106-spec-search-and-places.md) | Search and places | Final | 2026-01-05 |
| [SPEC-0107](active/0107-spec-jobs-and-webhooks.md) | Jobs and webhooks | Final | 2026-01-05 |
| [SPEC-0108](active/0108-spec-security-and-abuse-protection.md) | Security and abuse protection | Final | 2026-01-05 |
| [SPEC-0109](active/0109-spec-testing-quality-and-ci.md) | Testing, quality, and CI | Final | 2026-01-05 |
| [SPEC-0110](active/0110-spec-deployment-and-operations.md) | Deployment and operations (Vercel + Supabase + Upstash) | Final | 2026-01-05 |
| [SPEC-0111](active/0111-spec-payments-and-stripe.md) | Payments and Stripe (server-only + webhooks) | Final | 2026-01-19 |

## Archived Specifications

Completed, accepted, implemented, and superseded specs (plus historical migrations) are stored in [`archive/`](archive/). Refer to individual files there for status history and outcomes.

Notable archived specs:

- **SPEC-0036** (Attachments V2 Vercel Blob) — Superseded by SPEC-0105 (Supabase Storage + ingestion)
- **SPEC-0037** (Attachments V2 Supabase Storage) — Superseded by SPEC-0105
- **SPEC-0038** (BotID integration) — Superseded by SPEC-0108

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
