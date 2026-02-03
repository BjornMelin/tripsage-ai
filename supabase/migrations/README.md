# TripSage Supabase migrations (pre-deployment)

TripSage is **pre-deployment**: the database schema is primarily **squashed** into a single, deterministic baseline migration for maximum local reproducibility.

A small number of **incremental** migrations are included for targeted fixes that are safer to apply as patch migrations (for example, Postgres/RLS performance improvements) while still keeping local resets deterministic.

## Canonical schema

- `supabase/migrations/20260120000000_base_schema.sql` — baseline schema (tables, RLS, RPCs, indexes, Storage + Realtime policies).
- `supabase/migrations/20260126000000_rls_chat_auth_uid_select.sql` — RLS performance patch (chat policies).
- `supabase/migrations/20260202000000_rls_auth_uid_select.sql` — RLS performance patch (non-chat policies).
- `supabase/migrations/archive/` — historical split migrations (read-only, not applied by the Supabase CLI).

## Local workflow (recommended)

```bash
pnpm supabase:bootstrap
pnpm supabase:reset:dev
pnpm supabase:typegen
```

## Editing rules (until the first remote deploy)

- Planned schema changes: edit `supabase/migrations/20260120000000_base_schema.sql`.
- Targeted patch fixes: add a new incremental migration via `supabase migration new ...`.
- Then run `pnpm supabase:reset:dev` and `pnpm supabase:typegen`.

When TripSage starts deploying to remote Supabase environments, prefer incremental migrations (`supabase migration new ...`) for all changes and stop editing the baseline migration in-place.
