# ADR-0019: Canonicalize chat service via FastAPI backend

**Date**: 2025-10-23

## Status

Accepted

## Context

We previously considered hosting a native Next.js AI SDK v5 route for chat streaming. The backend already exposes a stable FastAPI `/api/v1/chat/` endpoint with cookie-based auth integration and domain logic (tools, memory, rate limits). Duplicating behavior in a Next route introduces drift and increases maintenance.

Recent Next.js 16 guidance clarifies proxy.ts as the network boundary and encourages Route Handlers as thin BFFs rather than duplicate service layers. The Vercel AI SDK v5 can adapt arbitrary streams to `UIMessage` streams, so a BFF can forward backend responses without owning domain logic.

## Decision

- The FastAPI `/api/v1/chat/` endpoint is the single source of truth for all chat functionality (sessions, messages, WebSockets, agents).
- The Next.js native chat Route Handler is fully removed; the frontend calls the FastAPI backend directly using `${NEXT_PUBLIC_API_URL}/api/v1/chat/`, with credentials included for auth.
- The `use-chat-ai` hook interfaces directly with the FastAPI backend, handling auth via `credentials: 'include'` and using the public API URL.
- If a local BFF Route Handler is ever reintroduced, it must only forward requests, propagate auth headers, statuses, and minimally adapt stream output to the AI SDK `UIMessage` format—never re-implementing backend domain logic.
- All unused AI SDK client dependencies and chat Route Handler code in Next.js are removed unless still required for other features.

## Consequences

### Positive

- Single source of truth for chat orchestration and tooling.
- Simpler frontend; fewer moving parts and less streaming protocol surface.
- Reuses existing backend observability, limits, and error handling.

### Negative

- Loses some direct integration opportunities with AI SDK server helpers in Next.
- Local development requires backend to be running for chat features.

### Neutral

- The frontend can still render UIMessage-like structures if the backend format evolves; no UI changes are mandated now.

## Alternatives Considered

### Native Next.js AI SDK v5 route

Rejected for now due to duplication risk and added maintenance. Could be reconsidered if we migrate tooling entirely to Next.

## References

- FastAPI service docs (internal)
- Frontend implementation: `frontend/src/hooks/use-chat-ai.ts`
- Next.js 16 blog (proxy.ts, caching/tagging updates, SWR via `revalidateTag(tag, profile)`).
- AI SDK v5 server streaming and `toUIMessageStreamResponse` examples.
