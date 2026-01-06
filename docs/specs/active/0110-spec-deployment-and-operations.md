# SPEC-0110: Deployment and operations (Vercel + Supabase + Upstash)

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

## Goals

- One-command deploy via Vercel.
- Safe secret handling.
- Repeatable environment bootstrapping.

## Requirements

- Vercel Project configured with:
  - Supabase integration (env vars)
  - Upstash integration (env vars)
  - BotID enabled for configured routes

- Environment validation at runtime using Zod:
  - fail fast on missing/invalid env vars

## References

```text
Next.js on Vercel: https://vercel.com/docs/frameworks/full-stack/nextjs
Vercel docs: https://vercel.com/docs
Supabase Next.js quickstart: https://supabase.com/docs/guides/getting-started/quickstarts/nextjs
Upstash: https://upstash.com/docs
```
