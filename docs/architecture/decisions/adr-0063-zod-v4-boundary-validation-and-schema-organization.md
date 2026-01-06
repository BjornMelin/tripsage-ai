# ADR-0063: Zod v4 boundary validation and schema organization

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2026-01-05  
**Category**: fullstack  
**Domain**: validation, type safety

## Context

TripSage integrates multiple untrusted boundaries:

- Browser inputs
- URL params
- LLM tool inputs
- Webhooks (Supabase/QStash)
- External APIs

TypeScript alone cannot protect these boundaries.

## Decision

- Zod v4 is the single runtime validation standard.
- All boundary inputs are parsed with Zod, with early returns on failure.
- All boundary outputs are also validated when:
  - coming from external systems (webhooks, third-party APIs)
  - or used as tool inputs to agents

Schema organization:

- Feature-local schemas live in `src/features/<feature>/schemas.ts`.
- Shared primitives (ids, pagination, money, geo, date ranges) live in `src/domain/schemas/*`.
- “Strict by default”: use strict objects unless there is an explicit reason to accept unknown keys.

Zod v4 constraints:

- No `deepPartial` (use shallow `partial()` or explicit nested partials).
- Use the `error` param (not deprecated message patterns) for custom messages where applicable (example: `z.string().min(5, { error: "Value must be at least 5 characters" })`).

## Consequences

- Strong boundary safety and consistent error formatting.
- Predictable API contracts for Server Actions, Route Handlers, and agent tools.
- Slight upfront effort to keep schemas organized, but major long-term maintainability gain.

## References

```text
Zod v4 migration guide: https://zod.dev/v4/changelog
Zod API reference: https://zod.dev/api
Zod error customization: https://zod.dev/error-customization
Zod strict vs loose object (JSON schema notes): https://zod.dev/json-schema
```
