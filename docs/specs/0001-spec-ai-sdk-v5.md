# Spec: AI SDK v5 Migration (Client + Route)

**Version**: 1.1.0
**Status**: Accepted
**Date**: 2025-10-24

## Objective

Align the AI-related client code and documentation with ADR-0019. The frontend calls the FastAPI chat endpoint directly; no Next.js AI SDK Route Handler is maintained. We retain AI SDK references in docs for future consideration only.

## Implementation Checklist

Client

- [x] Update `src/hooks/use-chat-ai.ts` to POST to `${NEXT_PUBLIC_API_URL}/api/chat/stream` (SSE) using `credentials: 'include'`, progressively updating a placeholder assistant message.

Server Route

- [x] No Next.js chat Route Handler; canonical endpoint remains FastAPI `/api/v1/chat/` (see ADR-0019).

Transport

- [ ] If custom endpoint or headers are required, use `transport` options or `headers` in `useChat` calls.

Docs

- [x] ADR-0015 documents the original v5 migration.
- [x] ADR-0019 documents canonicalization to FastAPI.

Validation

- [ ] Manual: send a prompt via `use-chat-ai` and verify streamed deltas update the placeholder message; verify cookies included.

## Changelog

- 1.1.0 (2025-10-24) — Switch documentation from JSON response to SSE streaming via `/api/chat/stream`; add version metadata.
- 1.0.0 (2025-10-23) — Initial alignment to ADR-0019 (FastAPI canonical backend).
