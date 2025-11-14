# Supabase Canonical Schema Plan

## Goal

Establish a single-source-of-truth schema (`supabase/schema.sql`) plus optional `seed.sql` that can create a brand-new Supabase project with all Tripsage AI capabilities (trip planning, AI memories, RAG embeddings, BYOK gateway, storage, realtime, webhooks) in one command, eliminating conflicting migrations.

## Extension Strategy

| Extension | Required By | Notes |
| --- | --- | --- |
| `pgcrypto` | UUID generation, hashing | Needed for `gen_random_uuid()` PKs + API key hashes. |
| `pg_trgm` | fuzzy search, Supabase text search | Already used in search tables + caching. |
| `vector` | AI memories, accommodation embeddings | Standardize on `extensions.vector` with dimension 1536; avoid duplicate enables. |
| `pgjwt` | Supabase helpers | Already in base schema; keep for auth RPCs. |
| `pg_stat_statements` | DB monitoring | Provide default but optional. |
| `pg_net` | Webhook + outbound HTTP | Only enable if webhook functions still needed; otherwise drop. |
| `http` | Webhook functions (if using http extension) | Evaluate vs `pg_net` when finalizing send logic. |
| `pgsodium` or `supabase_vault` | BYOK/API keys | Choose based on project plan (Vault preferred). |
| `realtime` | Supabase realtime policies | Already required for topic helpers. |
| `pgmq` | Queueing (if still using) | Enable only if referenced functions remain. |

## Table Inventory (Target Schema)

| Domain | Tables | Notes |
| --- | --- | --- |
| Trip Core | trips, flights, accommodations, transportation, itinerary_items, bookings, trip_collaborators | Use UUID PKs; cascade delete on trip_id/user_id. |
| AI Memories & RAG | memories, session_memories, accommodation_embeddings | Rename RAG table to `accommodation_embeddings` (TEXT PK referencing EPS ID), store vector(1536) + metadata + optional user_id. |
| Integrations / BYOK | user_gateway_configs, user_api_keys (vault-backed), api_gateway_configs, user_settings | Consolidate API key storage tables; only store vault path + hashed metadata. |
| Storage + Files | storage bucket records (insert rows), file_versions, file_processing_queue | Seed default buckets (uploads, itinerary-assets). |
| Telemetry / Webhooks | webhook_configs, webhook_logs, webhook_events, notifications, system_metrics | Keep only actively used ones. |
| Search Cache | search_destinations, search_activities, search_flights, search_hotels | Validate ongoing need; can drop if unused. |
| Misc Helpers | chat_sessions, chat_messages, chat_tool_calls, file_attachments | |

## Function / RPC Inventory (Keep vs. Review)

- **Keep (actively used)**
  - `match_accommodation_embeddings` (reads from `accommodation_embeddings`; accepts `vector(1536)`).
  - Vault helpers: `insert_user_api_key`, `get_user_api_key`, `delete_user_api_key`, `touch_user_api_key`.
  - Gateway config RPCs: `upsert_user_gateway_config`, `get_user_gateway_base_url`, `delete_user_gateway_config`, `get_user_allow_gateway_fallback`.
  - Realtime helpers: `rt_topic_prefix`, `rt_topic_suffix`, `rt_is_session_member`.
  - `update_updated_at_column` triggers for tables needing audit.

- **Review / trim** (validate actual usage before porting)
  - Massive suite of cleanup/maintenance functions in `20251027174600_base_schema.sql` (e.g., `optimize_vector_indexes`, `daily_cleanup_job`, webhook retry helpers). Keep only ones referenced by cron/policies.
  - Search caching helpers (may duplicate functionality now handled in app code).
  - Webhook execution helpers (`send_webhook_with_retry`, etc.) if app now uses Vercel Background Functions instead.

## RLS & Policy Plan

| Table / RPC | Intended Access |
| --- | --- |
| `trips`, `flights`, `accommodations` (trip) | Authenticated users with `auth.uid() = user_id` or collaborator via `trip_collaborators`. Service role full access. |
| `accommodation_embeddings` | Insert/update: service role only (embedding ingestion). Read: through `match_accommodation_embeddings` security definer returning filtered IDs; direct table RLS denies all except service role. |
| `memories`, `session_memories` | Authenticated owner only; service role full. |
| `user_gateway_configs`, `user_api_keys` | RLS on `user_id = auth.uid()`; insert/update via RPC to ensure secrets stored in Vault. |
| `webhook_*` tables | Owned by service role / automation; optionally allow user read of their own webhook configs. |
| `storage.objects` | Use Supabase standard storage policies referencing `request.auth.uid()`. Seed bucket metadata in schema. |

## Seeds

- Insert storage buckets (`uploads`, `documents`, `trip-assets`).
- Insert default system settings rows (e.g., `api_gateway_configs` for vercel gateway?).
- Optionally insert sample accommodations for QA (non-prod only).

## Decision Log

### D1 – Canonical migration packaging

- **Options evaluated:**
  1. Single `schema.sql` + `seed.sql` (Option A)
  2. 3-phase ordered migrations (core, ai, integrations) (Option B)
  3. Supabase declarative schema beta (Option C)
- **Scores:**

| Option | Solution Leverage (35%) | Application Value (30%) | Maintenance Load (25%) | Adaptability (10%) | Weighted Score |
|--------|-------------------------|--------------------------|-------------------------|-------------------|---------------|
| **A** | **4.6** | **4.5** | **4.4** | **3.8** | **4.41 / 5** |
| B | 3.5 | 3.6 | 3.0 | 3.5 | 3.41 / 5 |
| C | 3.8 | 3.2 | 3.1 | 4.0 | 3.44 / 5 |

- **Decision:** Option A, score 4.41 (>9/10 when normalized). Adopt single schema + seed, archive old migrations for reference.

### D2 – Rename RAG table

- **Problem:** `public.accommodations` conflict between trip table and embedding table.
- **Decision:** Rename embedding table to `public.accommodation_embeddings`, keep trip table name to preserve domain semantics. Update RPCs and frontend persistence accordingly.

## Next Steps

1. Generate complete schema blueprint (columns/types/constraints for each table listed above) and verify against app usage.
2. Draft `schema.sql` with sections: extensions → enums/domains → tables → indexes → functions → policies → grants → seeds.
3. Use Supabase CLI (`supabase db reset`) to validate script end-to-end before deleting legacy migrations.
