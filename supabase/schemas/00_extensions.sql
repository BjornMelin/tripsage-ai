-- Supabase Extensions Setup
-- Description: Required extensions for TripSage database functionality
-- Dependencies: None (must be run first)
-- Version: 2.0 - Includes automation and real-time capabilities

-- ===========================
-- CORE EXTENSIONS
-- ===========================

-- Enable UUID extension for generating unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension for AI/ML embeddings and semantic search
-- Note: This extension provides vector data types and operations for storing
-- and querying high-dimensional vectors (embeddings) efficiently
CREATE EXTENSION IF NOT EXISTS "vector";

-- ===========================
-- AUTOMATION EXTENSIONS
-- ===========================

-- Enable pg_cron for scheduled job automation
-- Documentation: https://github.com/citusdata/pg_cron
-- Used for: Automated maintenance, data cleanup, cache expiration
CREATE EXTENSION IF NOT EXISTS "pg_cron";

-- Grant usage on pg_cron schema to postgres user
GRANT USAGE ON SCHEMA cron TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cron TO postgres;

-- Enable pg_net for HTTP requests from database
-- Documentation: https://github.com/supabase/pg_net
-- Used for: Webhook notifications, external API calls, Edge Function triggers
CREATE EXTENSION IF NOT EXISTS "pg_net";

-- ===========================
-- PERFORMANCE EXTENSIONS
-- ===========================

-- Enable pg_stat_statements for query performance monitoring
-- Used for: Identifying slow queries and optimization opportunities
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Enable btree_gist for advanced indexing capabilities
-- Used for: Optimizing complex queries with multiple conditions
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- ===========================
-- SECURITY EXTENSIONS
-- ===========================

-- Enable pgcrypto for encryption functions
-- Used for: API key encryption, sensitive data protection
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ===========================
-- EXTENSION CONFIGURATION
-- ===========================

-- Configure pg_cron settings
ALTER SYSTEM SET cron.database_name = 'postgres';

-- Configure pg_net settings for optimal performance
ALTER SYSTEM SET pg_net.batch_size = 200;
ALTER SYSTEM SET pg_net.ttl = '1 hour';

-- Configure pg_stat_statements
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = 10000;

-- Apply configuration changes
SELECT pg_reload_conf();

-- ===========================
-- REALTIME CONFIGURATION
-- ===========================

-- Create publication for real-time updates
-- This enables Supabase Realtime for specific tables
DROP PUBLICATION IF EXISTS supabase_realtime CASCADE;
CREATE PUBLICATION supabase_realtime;

-- Add tables to real-time publication
-- Only include tables that require real-time updates for performance
ALTER PUBLICATION supabase_realtime ADD TABLE trips;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE trip_collaborators;
ALTER PUBLICATION supabase_realtime ADD TABLE itinerary_items;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_tool_calls;

-- ===========================
-- EXTENSION VERIFICATION
-- ===========================

-- Create function to verify all extensions are properly installed
CREATE OR REPLACE FUNCTION verify_extensions()
RETURNS TABLE (
    extension_name TEXT,
    installed BOOLEAN,
    version TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ext.extname::TEXT,
        TRUE,
        ext.extversion::TEXT
    FROM pg_extension ext
    WHERE ext.extname IN (
        'uuid-ossp', 'vector', 'pg_cron', 'pg_net', 
        'pg_stat_statements', 'btree_gist', 'pgcrypto'
    )
    ORDER BY ext.extname;
END;
$$;

-- Note: Supabase automatically creates auth.users table with UUID primary keys
-- We reference auth.users(id) for all user relationships throughout the schema

-- Additional extensions to consider for future enhancements:
-- - pgvectorscale: Advanced vector indexing for improved embedding search performance
-- - pg_amqp: Message queue integration for advanced event processing
-- - pgtap: Testing framework for database functions and procedures
-- - plv8: JavaScript language for stored procedures (if needed)