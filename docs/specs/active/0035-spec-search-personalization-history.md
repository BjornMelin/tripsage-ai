# SPEC-0035: Search Personalization via History Tables

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2025-12-06

## Overview

Capture recent user search activity to personalize accommodations/flight suggestions while keeping data bounded and non-cacheable by shared CDNs.

## Data model

- Tables: `search_hotels`, `search_flights` (existing).
- Fields used for personalization: `user_id`, `destination`/`origin`, `query_hash`, `created_at`, `expires_at`.
- Indexes:
  - `(user_id, created_at DESC)` for recency-based personalization.
  - `(query_hash)` for cache lookups.
  - `(expires_at)` for TTL enforcement.

## Retention & cleanup

- `expires_at` set per entry; a pg_cron job runs daily to delete rows past `expires_at`.
- Target window: keep only the most recent history relevant to personalization; defaults to 30–90 days depending on feature, bounded by `expires_at`.

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

## References

- ADR-0056 (Popular Routes - Flights)
- pg_cron cleanup added in `supabase/migrations/20251122000000_base_schema.sql`
