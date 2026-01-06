# SPEC-0110: Deployment on Vercel (Supabase + Upstash)

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

## Goals

- One-command deploy via Vercel.
- Safe secret handling.
- Repeatable environment bootstrapping.

For operational runbooks (monitoring, alerting, incident response, secret rotation), see [Deployment Runbook](../../runbooks/deployment-vercel.md).

## Non-goals

- Manual deployments or self-hosted infrastructure (Vercel is the canonical platform).
- Providing production runbooks for incident response or scaling (see [Deployment Runbook](../../runbooks/deployment-vercel.md)).
- Supporting multiple deployment platforms (Vercel is the standardized target).

## Requirements

- Vercel Project configured with:
  - Supabase integration (env vars)
  - Upstash integration (env vars)
  - BotID (Vercel's bot detection) enabled for configured routes (see [ADR-0059](../../architecture/decisions/adr-0059-botid-chat-and-agents.md))

- Environment validation at runtime using Zod:
  - Schema: `src/domain/schemas/env.ts`
  - Fails fast on missing/invalid env vars in production (check deployment logs for Zod validation errors)

- Required environment variables:
  - Supabase:
    - NEXT_PUBLIC_SUPABASE_URL
    - NEXT_PUBLIC_SUPABASE_ANON_KEY
    - SUPABASE_SERVICE_ROLE_KEY
  - Upstash:
    - UPSTASH_REDIS_REST_URL
    - UPSTASH_REDIS_REST_TOKEN

## Environment setup

1) Connect the Git repository to a Vercel project.
2) Configure Supabase and Upstash integrations (or set the required env vars manually).
3) Enable BotID for the routes described in ADR-0059.
4) Trigger a deployment and verify the build and runtime logs are free of env validation errors.

## References

```text
Next.js on Vercel: https://vercel.com/docs/frameworks/full-stack/nextjs
Vercel docs: https://vercel.com/docs
Supabase Next.js quickstart: https://supabase.com/docs/guides/getting-started/quickstarts/nextjs
Upstash: https://upstash.com/docs
Deployment Runbook: ../../runbooks/deployment-vercel.md
Environment Validation Schema: ../../../src/domain/schemas/env.ts
```
