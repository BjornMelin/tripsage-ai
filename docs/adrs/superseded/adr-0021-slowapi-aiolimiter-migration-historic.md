# ADR-0021: SlowAPI + Aiolimiter Migration (Historic)

**Version**: 1.0.0
**Status**: Superseded
**Date**: 2025-10-24
**Category**: backend
**Domain**: SlowAPI / Aiolimiter

## Context

An earlier attempt to document our migration to SlowAPI (request-level rate limiting) and aiolimiter (in-process concurrency control) produced an incomplete/invalid ADR (numbered 0012). To keep an accurate record without reusing numbers, this ADR captures the historical intent and outcome.

## Decision (Historical)

- Backend request rate limiting was standardized on SlowAPI. Storage backend resolves to async Redis when available; otherwise memory is used.
- `aiolimiter` was considered for local, per-process throttling of specific internal paths (e.g., CPU-bound operations or fan-out loops) and remains available for targeted use, but not as the primary request-rate limiter.

## Consequences

- SlowAPI applies consistent request envelopes across FastAPI routes.
- `aiolimiter` may be applied judiciously inside services where SlowAPI is not applicable (e.g., internal loops), but must not be treated as a global limiter.

## Supersession

This ADR is superseded by ADR-0020 (Rate Limiting Strategy), which defines the current, canonical approach: Next.js Route Handlers use `@upstash/ratelimit` (env-gated) and FastAPI continues to use SlowAPI.

## References

- ADR-0020: Rate Limiting Strategy (Next @upstash/ratelimit + FastAPI SlowAPI)
- tripsage/api/limiting.py (SlowAPI setup)

## Changelog

- 1.0.0 (2025-10-24) — Historic record created; marked Deprecated; superseded by ADR-0020.
