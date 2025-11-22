-- Canonical TripSage schema loader (squashed)
-- Apply this file with psql to provision a fresh database.

\i ./migrations/20251122000000_base_schema.sql
\i ./migrations/202511220002_agent_config_seed.sql
