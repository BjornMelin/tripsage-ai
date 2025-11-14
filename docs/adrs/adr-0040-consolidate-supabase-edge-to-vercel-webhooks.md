# ADR-0040: Consolidate Supabase Edge (Deno) to Vercel Route Handlers + Database Webhooks

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-13
**Category**: Architecture/Platform
**Domain**: Backend, Integrations
**Related ADRs**: ADR-0014, ADR-0023, ADR-0028, ADR-0035
**Related Specs**: SPEC-0021, SPEC-0025

## Context

We previously ran several Supabase Edge Functions (Deno) for trip notifications, file processing, cache invalidation, and embeddings. While these were straightforward to wire from database triggers and lived within Supabase infra, they introduced a second runtime/toolchain (Deno) alongside our primary platform on Vercel (Next.js 16, Node/Edge runtimes). All functions were HTTP-bound and used the Supabase JS client and other HTTP SDKs (Upstash, Resend, OpenAI), with no Deno-specific capabilities required. Supabase provides Database Webhooks via `pg_net`/`supabase_functions.http_request` for external HTTP calls post-commit.

The product is deployed on Vercel and we manage operations there. Consolidating compute on Vercel simplifies observability, deployments, and secrets management while retaining Supabase for DB/Auth/Storage.

## Decision

We will migrate all Deno-based Supabase Edge Functions to Vercel Route Handlers (Node runtime) and Background Functions. Database events will invoke Vercel endpoints via Supabase Database Webhooks using `supabase_functions.http_request`, signed with an HMAC header. We will decommission the Supabase Edge Functions and associated CLI deploy steps after a dual-run period.

## Consequences

### Positive

- Single runtime and deployment surface (Vercel) → reduced cognitive and operational load
- Unified logs/observability and error handling across the app tier
- Region pinning and Background Functions accommodate latency and long-running tasks
- Easier testing and CI by removing Deno bundling/lockfile nuances

### Negative

- Slight additional network hop between Supabase and Vercel for webhook delivery
- Service-role or restricted DB key needs safe storage in Vercel with least privilege

### Neutral

- Triggers become explicit HTTP webhooks instead of intra-platform calls; behavior is equivalent for our use cases

## Alternatives Considered

### Keep Supabase Edge Functions (Deno)

Retain proximity to DB/storage and internal trigger simplicity. Rejected due to duplicated runtime/tooling, split observability, and no strict need for Deno-only features.

### Hybrid (some functions in Deno, some in Vercel)

Adds complexity without clear benefit. If we later introduce ultra-low-latency internal jobs, we can reintroduce a single Deno function narrowly scoped.

## References

- Spec: docs/specs/0021-spec-supabase-webhooks-vercel-consolidation.md
- Supabase Database Webhooks: <https://supabase.com/docs/guides/database/webhooks>
- pg_net extension: <https://supabase.com/docs/guides/database/extensions/pg_net>
- Next.js Route Handlers: <https://nextjs.org/docs/app/building-your-application/routing/route-handlers>
- Vercel Functions, Regions, Duration, Cron: <https://vercel.com/docs/functions>, <https://vercel.com/docs/functions/configuring-functions/region>, <https://vercel.com/docs/functions/configuring-functions/duration>, <https://vercel.com/docs/cron-jobs>
