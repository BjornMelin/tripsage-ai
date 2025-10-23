# ADR-0019: Canonicalize Chat Service on FastAPI; Remove Next.js Native Route

## Status

Accepted – 2025-10-23

## Context

We briefly introduced a Next.js native AI SDK chat Route Handler to stream UI messages. The backend already exposes a comprehensive ChatService via FastAPI, powering REST, WebSockets, agents, persistence, rate limiting, and observability. Keeping both created duplicated orchestration and risked divergence in session state and behavior.

Recent Next.js 16 guidance clarifies proxy.ts as the network boundary and encourages Route Handlers as thin BFFs rather than duplicate service layers. The Vercel AI SDK v5 can adapt arbitrary streams to `UIMessage` streams, so a BFF can forward backend responses without owning domain logic.

## Decision

- Make the FastAPI ChatService the single source of truth for chat (sessions, messages, WebSockets, agents).
- Remove the Next.js native chat Route Handler. The UI calls the backend directly at `${NEXT_PUBLIC_API_URL}/api/v1/chat/`.
- If a stable app-local URL is required later, a thin BFF Route Handler may be reintroduced. It must forward auth headers, propagate status codes, and transform the backend stream to the AI SDK `UIMessage` format without re-implementing domain rules.

## Consequences

- Eliminates duplicate orchestration (KISS/DRY/YAGNI).
- Preserves backend cross-cutting concerns (auth, rate limits, telemetry) and agent/WebSocket integrations.
- Frontend hook refactored to call backend endpoints with `fetch` using `credentials: "include"` and consistent error handling.

## Alternatives Considered

- Pure Next.js chat service (delete FastAPI): high-risk rewrite of agents/WS/tests; rejected.
- Keep both implementations: violates single-source and increases maintenance burden; rejected.

## References

- Next.js 16 blog (proxy.ts, caching/tagging updates, SWR via `revalidateTag(tag, profile)`).
- AI SDK v5 server streaming and `toUIMessageStreamResponse` examples.

