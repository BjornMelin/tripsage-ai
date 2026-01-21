# TripSage Supabase Project

Supabase infrastructure for TripSage.

**Pre-deployment note:** the database schema is **squashed** into a single definitive migration for maximum local reproducibility. Historical split migrations are kept under `supabase/migrations/archive/` for reference only.

## Project Structure

```text
supabase/
├── migrations/
│   ├── 20260120000000_base_schema.sql    # Squashed schema: tables, RLS, RPCs, indexes, Storage + Realtime policies
│   ├── archive/                          # Archived legacy migrations (read-only)
│   └── README.md                         # Migration documentation
├── config.toml                           # Supabase CLI configuration
├── schema.sql                            # Schema loader (psql include)
├── seed.sql                              # Optional SQL seed (not used by repo seed scripts)
└── README.md                             # This file
```

## Local Development (recommended)

TripSage runs Supabase local via repo scripts (see `package.json`):

```bash
pnpm supabase:bootstrap   # start + apply schema + print status/keys
pnpm supabase:reset:dev   # clean reset + deterministic seed dataset
pnpm supabase:typegen     # regenerate src/lib/supabase/database.types.ts
```

## Documentation

- `docs/runbooks/supabase.md` — local stack, seed profiles, typegen
- `docs/development/core/local-supabase-rag-e2e.md` — end-to-end local Supabase + RAG verification
- `docs/operations/runbooks/database-ops.md` — migration workflow, operational checks

## Production Migration Strategy (future)

When TripSage starts deploying to remote Supabase environments, switch back to incremental migrations (`supabase migration new ...`) instead of editing the squashed file.
