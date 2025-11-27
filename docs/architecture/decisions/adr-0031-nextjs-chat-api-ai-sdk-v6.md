# ADR-0031: Next.js Chat API (SSE + Non-Stream) with AI SDK v6

**Status**: Accepted
**Date**: 2025-11-02
**Category**: frontend
**Domain**: Chat API / Streaming

## Context

We are migrating chat endpoints to Next.js App Router using AI SDK v6. This consolidates SSE and non-stream implementations beside the UI, integrates BYOK provider resolution, and standardizes token budgeting and usage metadata.

## Decision

- Implement `POST /api/chat` (non-stream) using `generateText` with safe token clamping and usage metadata.
- Implement `POST /api/chat/stream` (SSE) using `streamText(...).toUIMessageStreamResponse` with start/final/usage metadata and graceful error handling.
- Enforce SSR-only secrets with Supabase auth and Upstash RL (stream: 40/min per user+IP). No RL on non-stream by default.
- Validate attachments (image/* only) and reject others with `{ error: 'invalid_attachment' }`.
- Persist assistant messages best‑effort on finish with usage metadata.
- Remove legacy Python chat routes and any old Next.js v5 chat route; no back-compat.

## Consequences

### Positive

- Simpler BFF boundary; full leverage of AI SDK v6 stream helpers and usage.
- Deterministic tests (DI handlers + thin adapters).

### Negative

- Requires Supabase SSR client config and Upstash envs for RL.

## Alternatives Considered

- Keep FastAPI as canonical chat service: rejected due to duplication and drift; Next.js routes now own chat API.

## References

- AI SDK v6: Generating Text, Streaming, UI Message Streams
