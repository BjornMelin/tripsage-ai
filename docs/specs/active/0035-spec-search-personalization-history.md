# SPEC-0035: Search Personalization via History Tables

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2025-12-06

## Overview

Capture recent user search activity to personalize accommodations/flight suggestions while keeping data bounded and non-cacheable by shared CDNs.

## Data model

- Tables: `search_hotels`, `search_flights` (existing).
- Fields used for personalization: `user_id`, `destination`/`origin`, `query_hash`, `created_at`, `expires_at`.
- Query hash: computed as SHA-256 over the normalized search params: lowercased keys sorted lexicographically, values normalized (dates ISO, arrays sorted), joined with `\n`, encoded as hex. Canonical implementation: `src/lib/queries/hash-search.ts`.
- Indexes:
  - `(user_id, created_at DESC)` for recency-based personalization.
  - `(query_hash)` for cache lookups.
  - `(expires_at)` for TTL enforcement.

## Retention & cleanup

- `expires_at` set per entry; a pg_cron job runs daily to delete rows past `expires_at`.
- Target window per feature:

| Feature | Default days | Override | Notes |
|---------|--------------|----------|-------|
| Flight search history | 90 | `SEARCH_PERSONALIZATION_TTL_FLIGHTS_DAYS` | Longer relevance for route planning |
| Hotel search history | 30 | `SEARCH_PERSONALIZATION_TTL_HOTELS_DAYS` | Higher turnover; shorter window |

- All entries respect their `expires_at`; cleanup enforces this daily. Defaults can be tightened/extended via the env vars above (or `SEARCH_PERSONALIZATION_TTL_DAYS` as a global fallback).

## Access & caching

- API routes using this history are **auth-required**; responses must send `Cache-Control: private, no-store`.
- Upstash/Redis cache keys should be user-scoped (e.g., `popular-hotels:user:{id}`) to avoid cross-user leakage.
- If anonymous access is ever needed, use a separate public endpoint with purely generic data.

## Usage pattern

1) Query the history table ordered by `created_at DESC` for the current user.
2) Aggregate to top destinations/origins; cap to 10–20 items.
3) Fallback to curated global defaults when no history exists.

## Observability

- Emit telemetry span `search.personalization` with counters for `history_hit` vs `fallback_global`.
- Monitor daily cleanup job success and row counts to detect TTL drift.

## Error Handling & Edge Cases

- **NULL `expires_at`**: should never be persisted; queries must filter out NULLs. Validation sets `expires_at` on insert based on feature-specific TTL.
- **Cleanup failures**: pg_cron failures raise alerts; rerun job manually if rows accumulate (see ops runbook). Deletes are idempotent and batched to avoid long locks.
- **Concurrent cleanup vs queries**: cleanup uses small batch deletes to minimize locking; readers may see slightly stale rows but no partial responses.
- **Cache invalidation**: when cleanup runs, invalidate user-scoped Redis keys (e.g., `popular-hotels:user:{id}`) to avoid serving stale history-driven suggestions.

## References

- ADR-0056 (Popular Routes - Flights)
- pg_cron cleanup added in `supabase/migrations/20251122000000_base_schema.sql`
