# ADR-0069: Repo structure (feature-first) and server-only boundaries

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2026-01-05  
**Category**: engineering  
**Domain**: maintainability, performance, bundling

## Context

TripSage is feature-rich (trips, chat, search, memory, attachments, jobs). A flat “technical layer” structure tends to create:

- unclear ownership
- circular dependencies
- accidental client bundling of server-only code

## Decision

- Use a feature-first structure under `src/features/<feature>/...`.
- Enforce server-only boundaries:
  - DB access only inside `src/server/*`.
  - Server Actions in `src/server/actions/*`.
  - Cached reads in `src/server/queries/*`.
- UI:
  - shadcn/ui only under `src/components/ui`.
  - feature UI lives under each feature.
- API (Route Handlers) only when required (streaming, webhooks).

## Consequences

- Better navigability and ownership.
- Reduced client bundle risk.
- Requires lint rules and review discipline to prevent boundary violations.

## References

```text
Next.js App Router fundamentals: https://nextjs.org/docs/app
Next.js Route Handlers: https://nextjs.org/docs/app/getting-started/route-handlers
```
