# ADR-0071: Unknown thrown values and client error boundary policy

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2026-01-19  
**Category**: Frontend / Reliability  
**Domain**: Error handling / UX  
**Related ADRs**: ADR-0046, ADR-0061, ADR-0062, ADR-0063  
**Related Specs**: SPEC-0100, SPEC-0109

## Context

- JavaScript allows throwing any value (not just `Error` instances). In practice, `throw "string"` and other non-`Error` throws occur.
- `react-error-boundary@6.1.0` updates its boundary error type from `Error` to `unknown`, requiring downstream code to stop assuming `Error`.
- Next.js route and rendering error boundaries can surface `unknown` shapes, sometimes with additional fields like `digest`.
- TripSage must:
  - avoid unsafe casts (`as unknown as T` is forbidden in production code)
  - render user-safe error UI
  - preserve diagnostic signal for telemetry without leaking secrets/PII

## Decision

We standardize on “unknown everywhere at the boundary” and centralize normalization:

1) **Treat boundary errors as `unknown`**
   - Error boundary fallback renderers, `onError` handlers, and service error sinks must accept `unknown`.

2) **Use a canonical normalizer**
   - Client-side thrown values are normalized with `normalizeThrownError(thrown)` in `src/lib/client/normalize-thrown-error.ts`.
   - The normalizer:
     - uses `getErrorMessage()` from `react-error-boundary` for safe message extraction
     - preserves optional diagnostic fields (`digest`, `stack`) when present and string-typed
     - produces an `Error` instance for downstream logging/telemetry

3) **User-facing messaging is conservative**
   - UI prefers stable, actionable fallbacks (“Something went wrong”, “Unable to load…”) over leaking internal details.
   - When a message is shown, it is derived via `getErrorMessage()` and/or the normalizer and must be safe for untrusted content.

## Consequences

### Positive

- Aligns with library typing (`react-error-boundary@6.1.0`) and JavaScript semantics.
- Eliminates unsafe assumptions about thrown values and reduces crash loops in error UI.
- Centralizes error normalization, reducing duplicated ad-hoc guards.

### Negative

- Requires additional defensive code in fallbacks and error handlers compared to assuming `Error`.

### Neutral

- Does not change server error handling policy; this ADR is focused on client/rendering boundaries.

## Alternatives Considered

### Continue treating errors as `Error`

Rejected: incorrect typing and unsafe behavior for non-`Error` thrown values; violates library upgrade constraints.

### Cast `unknown` to `Error` via `as unknown as Error`

Rejected: forbidden in production code and brittle; normalization must be explicit and safe.

## References

- `react-error-boundary` v6.1.0 release: <https://github.com/bvaughn/react-error-boundary/releases/tag/6.1.0>
- JavaScript `throw` semantics: any value may be thrown (language-level behavior)
