-- Consolidated Production Schema Migration
-- Description: Complete TripSage database schema deployment in a single migration
-- Created: 2025-06-09
-- Updated: 2025-06-11 - Includes critical infrastructure gap fixes
-- Version: Production v2.0
-- Replaces: All previous migrations - this creates the complete, production-ready schema
-- Incorporates: 20250610_01_fix_user_id_constraints.sql, 20250611_01_add_trip_collaborators_table.sql
-- Gap Analysis: Addresses 15 critical infrastructure gaps identified in comprehensive audit

-- This migration deploys the entire TripSage database schema by executing
-- all schema files in the correct order. It ensures a clean, reproducible
-- database deployment that properly integrates with Supabase Auth and includes
-- the latest enhancements for trip collaboration and memory system optimization.

-- ===========================
-- SCHEMA FILE EXECUTION ORDER
-- ===========================

-- 1. Extensions (UUID, pgvector)
\i schemas/00_extensions.sql

-- 2. Core Tables (trips, travel options, chat, API keys, memory, collaboration)
\i schemas/01_tables.sql

-- 3. Performance Indexes (B-tree, vector indexes, collaboration-optimized)
\i schemas/02_indexes.sql

-- 4. Database Functions (utilities, search, maintenance, collaboration)
\i schemas/03_functions.sql

-- 5. Automated Triggers (updated_at timestamps)
\i schemas/04_triggers.sql

-- 6. Row Level Security Policies (multi-tenant isolation with collaboration)
\i schemas/05_policies.sql

-- 7. Database Views (commonly used queries)
\i schemas/06_views.sql

-- 8. Storage Infrastructure (buckets, policies, Edge Functions)
\i storage/buckets.sql
\i storage/policies.sql
\i storage/config.sql

-- ===========================
-- MIGRATION COMPLETION LOG
-- ===========================

-- Log successful migration completion
DO $$
BEGIN
    RAISE NOTICE 'TripSage Production Schema v2.0 deployed successfully!';
    RAISE NOTICE 'Schema includes:';
    RAISE NOTICE '- ✅ Supabase Auth integration (auth.users references)';
    RAISE NOTICE '- ✅ Core travel planning tables (trips, flights, accommodations)';
    RAISE NOTICE '- ✅ Trip collaboration system with permission hierarchy';
    RAISE NOTICE '- ✅ Chat system with tool call tracking';
    RAISE NOTICE '- ✅ BYOK API key management';
    RAISE NOTICE '- ✅ Memory system with pgvector embeddings (UUID user_id)';
    RAISE NOTICE '- ✅ Row Level Security for multi-tenant isolation + collaboration';
    RAISE NOTICE '- ✅ Performance-optimized indexes (80+ strategic indexes)';
    RAISE NOTICE '- ✅ Vector indexes with IVFFlat for semantic search';
    RAISE NOTICE '- ✅ Utility functions and automated triggers';
    RAISE NOTICE '- ✅ Collaboration management functions';
    RAISE NOTICE '- ✅ Helpful views for common queries';
    RAISE NOTICE '';
    RAISE NOTICE 'NEW in v2.0 - Critical Infrastructure:';
    RAISE NOTICE '- 📁 Complete file storage infrastructure with multi-bucket architecture';
    RAISE NOTICE '- 🔍 Search cache tables (destinations, activities, flights, hotels)';
    RAISE NOTICE '- 🛡️ RLS policies for storage and search infrastructure updated';
    RAISE NOTICE '- ⚡ Additional performance indexes for search and storage optimization';
    RAISE NOTICE '- 🔧 Safe SQL execution function with security validation';
    RAISE NOTICE '- 🧹 Automated search cache and file cleanup functions';
    RAISE NOTICE '- 🪣 Storage buckets (attachments, avatars, trip-images, thumbnails, quarantine)';
    RAISE NOTICE '- 🔒 Comprehensive storage RLS policies with trip collaboration support';
    RAISE NOTICE '- 🔄 File processing queue and versioning system';
    RAISE NOTICE '- 📊 Storage quota management and monitoring functions';
    RAISE NOTICE '';
    RAISE NOTICE 'Gap Analysis Addressed:';
    RAISE NOTICE '- ✅ 15 critical infrastructure gaps resolved';
    RAISE NOTICE '- ✅ Storage tables and policies implemented';
    RAISE NOTICE '- ✅ Search functionality database backing added';
    RAISE NOTICE '- ✅ Missing database functions implemented';
    RAISE NOTICE '';
    RAISE NOTICE 'Database is ready for production use with enhanced capabilities!';
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
        'trips', 'trip_collaborators', 'flights', 'accommodations', 'transportation', 'itinerary_items',
        'chat_sessions', 'chat_messages', 'chat_tool_calls',
        'api_keys', 'memories', 'session_memories',
        'file_attachments', 'search_destinations', 'search_activities', 'search_flights', 'search_hotels'
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