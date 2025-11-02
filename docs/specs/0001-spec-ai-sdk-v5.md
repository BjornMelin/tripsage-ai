# Spec: AI SDK v5 Migration (Client + Route)

**Version**: 1.1.0
**Status**: Superseded by ADR-0031 (2025-11-02)
**Date**: 2025-10-24

## Objective

Superseded by ADR-0031. Frontend hosts Next.js AI SDK v6 routes for chat: `/api/chat` (non-stream) and `/api/chat/stream` (SSE). Remove references to FastAPI chat as canonical and route via Next.js handlers.

## Implementation Checklist

Client

- [x] Update `src/hooks/use-chat-ai.ts` to POST to `${NEXT_PUBLIC_API_URL}/api/chat/stream` (SSE) using `credentials: 'include'`, progressively updating a placeholder assistant message.

Server Route

- [x] Next.js chat Route Handlers are canonical: `/api/chat` (JSON) and `/api/chat/stream` (SSE).

Transport

- [ ] If custom endpoint or headers are required, use `transport` options or `headers` in `useChat` calls.

Docs

- [x] ADR-0015 documents the original v5 migration.
- [x] ADR-0031 documents adoption of Next.js AI SDK v6 as canonical chat API.

Validation

- [ ] Manual: send a prompt via `use-chat-ai` and verify streamed deltas update the placeholder message; verify cookies included.

## Changelog

- 1.2.0 (2025-11-02) — Superseded: Next.js AI SDK v6 routes are canonical (ADR-0031). Remove FastAPI chat references.
