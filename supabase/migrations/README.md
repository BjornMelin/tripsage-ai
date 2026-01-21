# TripSage Supabase migrations (pre-deployment)

TripSage is **pre-deployment**: the database schema is intentionally **squashed** into a single, definitive migration for maximum local reproducibility.

## Canonical schema

- `supabase/migrations/20260120000000_base_schema.sql` — canonical schema (tables, RLS, RPCs, indexes, Storage + Realtime policies).
- `supabase/migrations/archive/` — historical split migrations (read-only, not applied by the Supabase CLI).

## Local workflow (recommended)

```bash
pnpm supabase:bootstrap
pnpm supabase:reset:dev
pnpm supabase:typegen
```

## Editing rules (until the first remote deploy)

- Edit `supabase/migrations/20260120000000_base_schema.sql`.
- Then run `pnpm supabase:reset:dev` and `pnpm supabase:typegen`.

When TripSage starts deploying to remote Supabase environments, switch back to incremental migrations (`supabase migration new ...`) and stop editing the squashed migration in-place.
