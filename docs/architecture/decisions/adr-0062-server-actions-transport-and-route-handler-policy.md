# ADR-0062: Server Actions transport and Route Handler policy

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2026-01-05  
**Category**: fullstack  
**Domain**: Next.js server actions, APIs

## Context

TripSage needs:

- Secure, server-only secrets for DB access and AI provider keys.
- Clean mutation semantics with strong typing and validation.
- Streaming AI endpoints and inbound webhooks, which require Route Handlers.

## Decision

- **Server Actions are the default transport for all app-initiated mutations**.
- **Route Handlers are reserved for**:
  1) Streaming AI responses (SSE or UI streams)
  2) External inbound webhooks (Supabase, QStash, provider callbacks)
  3) Public read APIs that are explicitly required (rare, versioned, documented)

Additionally:

- All Server Actions validate input with Zod v4 and return a standardized `Result<T, E>`.
- Client mutations use TanStack Query `useMutation` calling the Server Action, including optimistic updates and cache invalidation.

## Consequences

- Eliminates a large class of internal REST boilerplate.
- Reduces attack surface by keeping most operations behind server-only actions.
- Keeps streaming/webhook use cases on the correct primitive (Route Handlers).

## References

```text
Next.js Forms with Server Actions: https://nextjs.org/docs/app/guides/forms
Next.js Updating Data (Server Functions): https://nextjs.org/docs/app/getting-started/updating-data
Route Handlers: https://nextjs.org/docs/app/getting-started/route-handlers
React `useActionState`: https://react.dev/reference/react/useActionState
```
