-- Canonical TripSage schema loader
-- Apply this file with psql to provision a new database with all migrations.

\i ./migrations/20251027174600_base_schema.sql
\i ./migrations/202510271701_realtime_helpers.sql
\i ./migrations/202510271702_storage_infrastructure.sql
\i ./migrations/20251027_01_realtime_policies.sql
\i ./migrations/20251028_01_update_webhook_configs.sql
\i ./migrations/20251030000000_vault_api_keys.sql
\i ./migrations/20251030002000_vault_role_hardening.sql
\i ./migrations/20251113000000_gateway_user_byok.sql
\i ./migrations/20251113024300_create_accommodations_rag.sql
\i ./migrations/20251113024301_create_bookings_table.sql
\i ./migrations/20251113034500_webhooks_consolidated.sql
\i ./migrations/20251114120000_update_accommodations_embeddings_1536.sql
