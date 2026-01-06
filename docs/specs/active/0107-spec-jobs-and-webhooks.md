# SPEC-0107: Jobs and webhooks (Supabase + QStash)

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

## Goals

- Reliable background processing for:
  - attachment ingestion
  - RAG indexing
  - enrichment tasks (places, routes)
- Secure inbound webhooks from:
  - Supabase
  - QStash

## Requirements

- Every job handler must:
  - verify signature
  - enforce idempotency
  - emit structured logs
- Job payloads validated with Zod.

## References

```text
Upstash QStash retries: https://upstash.com/docs/qstash/features/retries
Upstash QStash local dev: https://upstash.com/docs/qstash/howto/local-development
Supabase webhooks: https://supabase.com/docs/guides/database/webhooks
```
