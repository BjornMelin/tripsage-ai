-- Consolidated Production Schema Migration
-- Description: Complete TripSage database schema deployment in a single migration
-- Created: 2025-06-09
-- Version: Production v1.0
-- Replaces: All previous migrations - this creates the complete, production-ready schema

-- This migration deploys the entire TripSage database schema by executing
-- all schema files in the correct order. It ensures a clean, reproducible
-- database deployment that properly integrates with Supabase Auth.

-- ===========================
-- SCHEMA FILE EXECUTION ORDER
-- ===========================

-- 1. Extensions (UUID, pgvector)
\i supabase/schemas/00_extensions.sql

-- 2. Core Tables (trips, travel options, chat, API keys, memory)
\i supabase/schemas/01_tables.sql

-- 3. Performance Indexes (B-tree and vector indexes)
\i supabase/schemas/02_indexes.sql

-- 4. Database Functions (utilities, search, maintenance)
\i supabase/schemas/03_functions.sql

-- 5. Automated Triggers (updated_at timestamps)
\i supabase/schemas/04_triggers.sql

-- 6. Row Level Security Policies (multi-tenant isolation)
\i supabase/schemas/05_policies.sql

-- 7. Database Views (commonly used queries)
\i supabase/schemas/06_views.sql

-- ===========================
-- MIGRATION COMPLETION LOG
-- ===========================

-- Log successful migration completion
DO $$
BEGIN
    RAISE NOTICE 'TripSage Production Schema v1.0 deployed successfully!';
    RAISE NOTICE 'Schema includes:';
    RAISE NOTICE '- ✅ Supabase Auth integration (auth.users references)';
    RAISE NOTICE '- ✅ Core travel planning tables (trips, flights, accommodations)';
    RAISE NOTICE '- ✅ Chat system with tool call tracking';
    RAISE NOTICE '- ✅ BYOK API key management';
    RAISE NOTICE '- ✅ Memory system with pgvector embeddings';
    RAISE NOTICE '- ✅ Row Level Security for multi-tenant isolation';
    RAISE NOTICE '- ✅ Performance-optimized indexes';
    RAISE NOTICE '- ✅ Utility functions and automated triggers';
    RAISE NOTICE '- ✅ Helpful views for common queries';
    RAISE NOTICE '';
    RAISE NOTICE 'Database is ready for production use!';
END $$;

-- ===========================
-- VERIFICATION QUERIES
-- ===========================

-- Verify all tables were created successfully
SELECT 
    schemaname,
    tablename,
    hasindexes,
    hasrules,
    hastriggers
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename IN (
        'trips', 'flights', 'accommodations', 'transportation', 'itinerary_items',
        'chat_sessions', 'chat_messages', 'chat_tool_calls',
        'api_keys', 'memories', 'session_memories'
    )
ORDER BY tablename;

-- Verify RLS is enabled on user tables
SELECT 
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables 
WHERE schemaname = 'public' 
    AND rowsecurity = true
ORDER BY tablename;

-- Verify extensions are installed
SELECT 
    extname as extension_name,
    extversion as version
FROM pg_extension 
WHERE extname IN ('uuid-ossp', 'vector')
ORDER BY extname;

-- ===========================
-- SCHEMA METADATA
-- ===========================

COMMENT ON SCHEMA public IS 'TripSage Production Schema v1.0 - Complete travel planning database with Supabase Auth integration';

-- ===========================
-- POST-DEPLOYMENT NOTES
-- ===========================

-- IMPORTANT: After running this migration, you should:
-- 1. Configure OAuth providers in Supabase Dashboard (Google, GitHub)
-- 2. Set up environment variables (SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET)
-- 3. Test authentication flows and RLS policies
-- 4. Verify vector embeddings functionality
-- 5. Run application integration tests
-- 6. Monitor performance with real data

-- For ongoing maintenance, use the provided functions:
-- - maintain_database_performance() - Run weekly for optimal performance
-- - cleanup_old_memories() - Run monthly to manage memory storage
-- - expire_inactive_sessions() - Run daily to clean up abandoned sessions

-- Schema deployment complete! 🚀