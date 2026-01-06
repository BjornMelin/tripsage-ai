# SPEC-0108: Security and abuse protection

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

## Goals

- Prevent abuse of AI endpoints and uploads.
- Reduce common web vulnerabilities (XSS, CSRF, injection, SSRF).
- Ensure secrets never reach the client bundle.

## Controls

- BotID on key routes
- Rate limiting with Upstash
- CSP and security headers
- Zod boundary validation
- RLS-first DB security

## Canonical Result and error shapes

This repo standardizes error handling to keep validation, logging, and client UX consistent.

### Server Actions

- Server Actions return `Result<T, ResultError>` (no thrown errors for expected failures).
- `ResultError` shape (serializable):
  - `error: string` (stable machine code)
  - `reason: string` (human-readable summary)
  - `issues?: z.core.$ZodIssue[]` (Zod v4 issues for debugging and form mapping)
  - `fieldErrors?: Record<string, string[]>` (dot-path keys, `"_form"` for root issues)

### Route Handlers

- Route Handlers validate all untrusted inputs (JSON bodies, params, search params) before use.
- Error responses must use the standardized JSON envelope:
  - `{ error: string, reason: string, issues?: z.core.$ZodIssue[] }`
- Prefer helper functions in `src/lib/api/route-helpers.ts` and `src/server/security/validate.ts` to enforce bounded reads and consistent responses.

## References

```text
BotID get started: https://vercel.com/docs/botid/get-started
Next.js CSP guide: https://nextjs.org/docs/app/guides/content-security-policy
OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
```
