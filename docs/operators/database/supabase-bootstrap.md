# Supabase Bootstrap Guide

This guide describes how to spin up a completely new Supabase project for TripSage AI using the consolidated schema and seeds.

## Prerequisites

- Supabase CLI installed (`supabase --version`).
- A Supabase account and project (for remote deployment).
- Local environment set up for this repo.

## Local Development Database

1. **Start the local Supabase stack**

   ```bash
   supabase start
   ```

2. **Reset the database and apply all migrations**

   Recommended (uses Supabase migration engine):

   ```bash
   supabase db reset
   ```

   Alternative single-command apply using the canonical loader (for non-Supabase Postgres):

   ```bash
   cd supabase
   psql "$DATABASE_URL" -f schema.sql
   ```

## Creating a New Supabase Project

1. **Create project in the Supabase Dashboard**

   - Note the `project-ref` and database connection string.

2. **Link the local repo to the project**

   ```bash
   supabase login
   supabase link --project-ref your-project-ref
   ```

3. **Push schema + seed data to the remote project**

   ```bash
   # Apply all migrations and (optionally) seed data
   supabase db push --include-seed
   ```

## Environment Variables

Set the following env vars for the frontend/backend to use the new project:

- `NEXT_PUBLIC_SUPABASE_URL` – Supabase project URL.
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` – public anon key.
- `SUPABASE_SERVICE_ROLE_KEY` – service role key (server-side only).

## Type Generation

After schema changes, regenerate TypeScript types for Supabase:

```bash
supabase gen types typescript --local > frontend/src/lib/supabase/database.types.ts
```

## RAG / Embeddings Expectations

- Embeddings are stored in `public.accommodation_embeddings` as 1536‑dimension vectors.
- Semantic search uses the `match_accommodation_embeddings` RPC, and the frontend calls it via the accommodations tool.
