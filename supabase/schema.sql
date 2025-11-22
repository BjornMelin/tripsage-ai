-- Canonical TripSage schema loader (squashed)
-- Apply this file with psql to provision a fresh database.

\i ./migrations/00000000000000_init.sql
\i ./migrations/202511220001_agent_config_backend.sql
