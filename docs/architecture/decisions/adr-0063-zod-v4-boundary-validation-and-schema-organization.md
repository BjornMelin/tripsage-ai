# ADR-0063: Zod v4 boundary validation and schema organization

**Version**: 1.1.0  
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

Canonical boundary helpers:

- **Canonical Result type**: `src/lib/result.ts`
  - `Result<T, E>`, `ok()`, `err()`
  - `ResultError` (serializable, client-safe) for Server Actions and shared boundaries
  - `zodErrorToFieldErrors()` for form-safe errors
- **Server entry boundary parsing** (Zod + bounded reads): `src/server/security/validate.ts`
  - `parseJson(request, schema)`
  - `parseFormData(formData, schema)`
  - `parseSearchParams(urlOrSearchParams, schema)`
  - `parseParams(params, schema)`
- **Route Handler helpers** (Next.js `NextRequest` adapters): `src/lib/api/route-helpers.ts`
  - `parseJsonBody(req)` (bounded read)
  - `validateSchema(schema, data)`
  - `parseNumericId(routeContext)`, `parseStringId(routeContext)`
  - `requireUserId(user)`
  - `errorResponse()`, `unauthorizedResponse()`, `forbiddenResponse()`, `notFoundResponse()`
- **Webhook signature + payload validation** (bounded raw reads): `src/lib/webhooks/payload.ts`
  - `parseAndVerify(req)` (single-pass body read → HMAC verify on bytes → JSON parse → Zod validation)
  - Used by `src/lib/webhooks/handler.ts` (`createWebhookHandler`)

Schema organization:

- Domain schemas live in `src/domain/schemas/*` and are imported via `@schemas/*`.
- Domain schema files group related schemas together (core + form + tool inputs) with section markers.
- “Strict by default”: use strict objects unless there is an explicit reason to accept unknown keys.

Zod v4 constraints:

- No `deepPartial` (use shallow `partial()` or explicit nested partials).
- Use the `error` param (not deprecated message patterns) for custom messages where applicable (example: `z.string().min(5, { error: "Value must be at least 5 characters" })`).
- Do not use deprecated Zod error helpers (`error.format()`, `error.flatten()`). Prefer `z.treeifyError(error)`, `z.flattenError(error)`, `z.prettifyError(error)`, or `error.issues` depending on the boundary.

Environment variables:

- Server-side env is validated once per process and accessed via the canonical server-only entrypoint `src/lib/env.ts`.
- Client-safe env access must use `src/lib/env/client.ts` to prevent accidental bundling of server secrets.

### Date/time parsing (Postgres + ISO 8601)

- Postgres `TIMESTAMPTZ` serialization often includes explicit timezone offsets (e.g., `+00:00`), not only `Z`.
- Canonical datetime validation uses `primitiveSchemas.isoDateTime` (`src/domain/schemas/registry.ts`), implemented as `z.iso.datetime({ offset: true, ... })`.
- Domain input schemas may accept date-only strings where user UX prefers dates (see SPEC-0102), but storage and API timestamps remain timezone-aware ISO strings.

## Consequences

- Strong boundary safety and consistent error formatting.
- Predictable API contracts for Server Actions, Route Handlers, and agent tools.
- Slight upfront effort to keep schemas organized, but major long-term maintainability gain.

## Post-acceptance updates (2026-01-19)

- Standardized ISO datetime validation to accept timezone offsets (fixes Supabase/Postgres round-trips where timestamps serialize as `+00:00`).

## References

```text
Zod v4 migration guide: https://zod.dev/v4/changelog
Zod API reference: https://zod.dev/api
Zod error customization: https://zod.dev/error-customization
Zod ISO datetime options: https://zod.dev/api?id=iso-datetimes
Zod strict vs loose object (JSON schema notes): https://zod.dev/json-schema
```
