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

## References

```text
BotID get started: https://vercel.com/docs/botid/get-started
Next.js CSP guide: https://nextjs.org/docs/app/guides/content-security-policy
OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
```
