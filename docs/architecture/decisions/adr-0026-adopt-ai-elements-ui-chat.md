# ADR-0026: Adopt AI Elements for Chat UI

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-01
**Category**: frontend
**Domain**: AI SDK / Next.js App Router
**Related ADRs**: [ADR-0023](adr-0023-adopt-ai-sdk-v6-foundations.md)
**Related Specs**: [SPEC-0008](spec-ai-sdk-v6-foundations.md)

## Context

The project previously shipped bespoke chat UIs and hooks spread across `frontend/src/components/chat` and `frontend/src/components/features/chat`, with mixed transports (websocket, custom SSE) and duplicated logic. AI SDK v6 ships AI Elements primitives and `useChat` that standardize message shape, streaming, and tool usage.

## Decision

- Use AI Elements primitives for conversation, messages, and prompt input.
- Standardize client transport on `@ai-sdk/react` with `DefaultChatTransport`.
- Provide a Next.js route handler at `frontend/src/app/api/chat/stream/route.ts` using `streamText(...).toDataStreamResponse()` to serve SSE.
- Add a simple first-party page `frontend/src/app/chat/page.tsx` to render the chat UI and wire prompt submission.

## Consequences

- Reduces bespoke UI code and aligns with AI SDK v6 patterns.
- Establishes a clear streaming contract (DataStream) for the chat UI.
- Enables progressive enhancement of tool usage visualization without custom protocols.

## Alternatives considered

- UI Message Stream with manual client parsing: deferred for simplicity; `useChat`+DataStream provides robust default behavior.
- Retrofitting custom chat components: rejected in favor of library-first approach.

## Migration notes

- Legacy chat pages/components remain available during transition to avoid broader test impact; future cleanup can remove superseded modules when back-compat is not required.
