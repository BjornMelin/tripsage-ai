# ADR-0015: Upgrade AI SDK to v5 (@ai-sdk/react) and useChat redesign

**Date**: 2025-10-23

## Status

Accepted

## Context

AI SDK v5 redesigns `useChat` (transport-based, no internal input state, UIMessage parts). Our client hook and route must adopt the new contract.

## Decision

- Use `@ai-sdk/react` for `useChat` and its `sendMessage({ text })` API.
- Update server route to return `toUIMessageStreamResponse()` from `streamText` and adopt tool `inputSchema`.

## Consequences

### Positive

- Better type-safety and tool support; improved streaming ergonomics.

### Negative

- Requires client UI to render `message.parts` and adjust optimistic updates.

### Neutral

- Route strategy is flexible: we can keep the current FastAPI proxy as long as it emits AI SDK UI message stream format, or move to a native AI SDK route later without client changes.

## Alternatives Considered

### Alternative 1 — Stay on AI SDK v4 (`ai/react`)

Rejected: v4 is superseded; v5 provides redesigned hooks, typed parts, and better tooling and provider support.

### Alternative 2 — Custom streaming protocol outside the SDK

Rejected: increases maintenance burden, reduces compatibility with SDK UI primitives, and loses provider/middleware ecosystem benefits.

## References

- AI SDK v5 quickstart for Next app router; `useChat` reference; v5 migration guide.
  - <https://ai-sdk.dev/docs/getting-started/nextjs-app-router>
  - <https://ai-sdk.dev/docs/reference/ai-sdk-ui/use-chat>
  - <https://ai-sdk.dev/docs/migration-guides/migration-guide-5-0>
