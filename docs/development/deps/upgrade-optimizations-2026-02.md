# Dependency Upgrade Optimizations (2026-02)

This repo upgraded to the latest compatible dependency set (Next.js 16 / React 19 / TypeScript 5.9 / Zod v4) and adds lightweight “guardrails” to prevent regressions into deprecated or contract-violating patterns.

## Guardrail Scripts

### Zod v4 style enforcement

Script: `scripts/check-zod-v4-usage.mjs`

Goal: keep Zod schemas aligned with the repo contract:

- Prefer top-level string helpers:
  - `z.email()` over `z.string().email()`
  - `z.uuid()` over `z.string().uuid()`
  - `z.url()` over `z.string().url()`
- Prefer ISO helpers:
  - `z.iso.datetime()` over `z.string().datetime()`

Commands:

- `pnpm check:zod-v4` (diff-based)
- `pnpm check:zod-v4:full` (scan all tracked `src/**`)

Exception marker (rare): add `zod-v4-ok:` on the violating line with a short justification.

### Route handler error response enforcement

Script: `scripts/check-api-route-errors.mjs`

Goal: enforce standardized error responses for `src/app/api/**`:

- Forbidden:
  - `NextResponse.json({ error: ... }, ...)`
  - `new Response(JSON.stringify({ error: ... }), ...)`
- Required:
  - Use helpers from `@/lib/api/route-helpers`:
    - `errorResponse({ error, reason, status })`
    - `unauthorizedResponse()`, `forbiddenResponse()`, `notFoundResponse()`

Commands:

- `pnpm check:api-route-errors` (diff-based)
- `pnpm check:api-route-errors:full` (scan all tracked `src/app/api/**`)

Exception marker (rare): add `api-route-error-ok:` on the violating line with a short justification.
