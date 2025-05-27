-- Rollback script for pgvector extensions
-- Migration: 20250526_01_enable_pgvector_extensions_rollback.sql
-- Purpose: Safely remove pgvector and vectorscale extensions if needed

-- =============================================================================
-- WARNING: DESTRUCTIVE OPERATION
-- =============================================================================
-- This script will remove pgvector and vectorscale extensions.
-- ALL VECTOR DATA AND INDEXES WILL BE LOST.
-- 
-- Before running this script:
-- 1. Backup all vector data if needed
-- 2. Document any existing vector indexes
-- 3. Ensure no applications are using vector operations
-- 4. Consider gradual rollback strategy for production
-- =============================================================================

-- Check for existing vector columns before rollback
DO $$
DECLARE
    vector_tables TEXT[];
    table_info TEXT;
BEGIN
    -- Find tables with vector columns
    SELECT array_agg(schemaname||'.'||tablename||'.'||attname)
    INTO vector_tables
    FROM pg_attribute a
    JOIN pg_class c ON a.attrelid = c.oid
    JOIN pg_namespace n ON c.relnamespace = n.oid
    JOIN pg_type t ON a.atttypid = t.oid
    WHERE t.typname = 'vector'
    AND NOT a.attisdropped
    AND a.attnum > 0;
    
    IF vector_tables IS NOT NULL THEN
        RAISE WARNING 'Found vector columns in tables: %', array_to_string(vector_tables, ', ');
        RAISE WARNING 'Consider backing up this data before proceeding with rollback';
    ELSE
        RAISE NOTICE 'No vector columns found - safe to proceed with extension removal';
    END IF;
END $$;

-- Drop vectorscale extension first (if it exists)
DO $$
BEGIN
    -- Check if vectorscale extension exists
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vectorscale') THEN
        DROP EXTENSION vectorscale CASCADE;
        RAISE NOTICE 'Successfully removed vectorscale extension';
    ELSE
        RAISE NOTICE 'vectorscale extension was not installed';
    END IF;
EXCEPTION 
    WHEN OTHERS THEN
        RAISE WARNING 'Failed to remove vectorscale extension: %', SQLERRM;
END $$;

-- Drop pgvector extension (if it exists)
DO $$
BEGIN
    -- Check if vector extension exists
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        DROP EXTENSION vector CASCADE;
        RAISE NOTICE 'Successfully removed vector extension';
    ELSE
        RAISE NOTICE 'vector extension was not installed';
    END IF;
EXCEPTION 
    WHEN OTHERS THEN
        RAISE WARNING 'Failed to remove vector extension: %', SQLERRM;
END $$;

-- Verify extensions are removed
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'All vector extensions successfully removed'
        ELSE 'Some vector extensions still exist: ' || string_agg(extname, ', ')
    END as rollback_status
FROM pg_extension 
WHERE extname IN ('vector', 'vectorscale');

-- Final cleanup check
DO $$
BEGIN
    -- Verify vector type no longer exists
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector') THEN
        RAISE NOTICE 'Rollback completed successfully - vector type removed';
    ELSE
        RAISE WARNING 'Vector type still exists - manual cleanup may be required';
    END IF;
END $$;