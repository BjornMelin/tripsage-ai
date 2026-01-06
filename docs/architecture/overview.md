# Architecture overview

TripSage AI is a Next.js App Router application optimized for:

- RSC-first rendering
- AI streaming and tool usage
- strict security boundaries
- low-maintenance, library-first implementation

## Key principles

- Server Components by default.
- Client Components only for interactivity.
- Server Actions for mutations.
- Route Handlers only for streaming and webhooks.
- Zod v4 for every boundary.
- Supabase RLS-first access model.

## Core subsystems

- Auth: Supabase SSR cookies
- Trips: Postgres tables + RLS + feature-first UI
- Chat: AI SDK v6 streaming + persistence
- Memory: pgvector + hybrid search + reranking
- Jobs: QStash + idempotent handlers
- Abuse protection: BotID + Upstash Ratelimit + CSP

```text
Next.js App Router: https://nextjs.org/docs/app
TanStack Query: https://tanstack.com/query/latest
AI SDK: https://ai-sdk.dev/docs
Supabase SSR: https://supabase.com/docs/guides/auth/server-side
```
