# ADR-0068: Security headers, CSP, BotID, and abuse controls

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2026-01-05  
**Category**: security  
**Domain**: OWASP controls, headers, bot defense

## Context

TripSage exposes high-value endpoints:

- chat and agent routes
- attachment uploads
- authentication flows

These are common bot and abuse targets.

## Decision

Layer defenses:

1) Strict server validation (Zod v4) for every boundary.
2) BotID protection on high-value routes.
3) Rate limiting (Upstash) on sensitive endpoints (per-user or per-ip where appropriate).
4) Strict response headers and CSP, with environment-aware dev relaxations.
5) Secure cookie configuration for Supabase SSR sessions.

Security standard baseline:

- Target OWASP ASVS Level 2 where applicable for a production SaaS-style web app.

## Consequences

- Substantially reduced abuse and common web exploit risk.
- Requires maintenance of CSP allowlists as integrations are added.

## References

```text
Next.js CSP guide: https://nextjs.org/docs/app/guides/content-security-policy
Next.js headers config: https://nextjs.org/docs/pages/api-reference/config/next-config-js/headers
Vercel BotID get started: https://vercel.com/docs/botid/get-started
Vercel BotID overview: https://vercel.com/docs/botid
OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
```
