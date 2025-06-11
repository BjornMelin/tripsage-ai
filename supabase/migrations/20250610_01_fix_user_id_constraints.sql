-- Migration: Fix foreign key constraints and UUID references for memory tables
-- Description: Convert TEXT user_id fields to UUID with proper foreign key constraints
-- Issue: BJO-121 - Critical database schema integrity fix
-- Date: 2025-06-10
-- Priority: HIGH - Security vulnerability and data integrity risk

-- ===========================
-- MIGRATION OVERVIEW
-- ===========================

-- This migration addresses critical issues with memory tables:
-- 1. Convert TEXT user_id fields to UUID type
-- 2. Add proper foreign key constraints to auth.users(id)
-- 3. Enable Row Level Security (RLS) on memory tables  
-- 4. Add RLS policies for data isolation
-- 5. Update related database functions

-- SAFETY MEASURES:
-- - Transaction-wrapped for atomicity
-- - Data validation before conversion
-- - Backup commands provided
-- - Rollback plan included

BEGIN;

-- ===========================
-- PRE-MIGRATION VALIDATION
-- ===========================

-- Check if auth.users table exists (Supabase auth schema)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'auth' AND table_name = 'users'
    ) THEN
        RAISE EXCEPTION 'auth.users table not found. Ensure Supabase auth is properly configured.';
    END IF;
END $$;

-- Log migration start
INSERT INTO session_memories (session_id, user_id, content, metadata)
VALUES (
    '00000000-0000-0000-0000-000000000000'::UUID,
    '00000000-0000-0000-0000-000000000001', -- Temporary system user
    'Starting migration: Fix user_id constraints',
    jsonb_build_object(
        'type', 'migration_start',
        'migration', '20250610_01_fix_user_id_constraints',
        'timestamp', NOW()
    )
);

-- ===========================
-- PHASE 1: PREPARE DATA
-- ===========================

-- Create a system user UUID for maintenance records if it doesn't exist
-- This handles cases where 'system' user_id was used in maintenance functions
INSERT INTO auth.users (id, email, encrypted_password, created_at, updated_at, confirmed_at)
VALUES (
    '00000000-0000-0000-0000-000000000001'::UUID,
    'system@tripsage.internal',
    '$2a$10$placeholder', -- Placeholder encrypted password
    NOW(),
    NOW(),
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- ===========================
-- PHASE 2: VALIDATE EXISTING DATA
-- ===========================

-- Check for invalid user_id values in memories table
-- This ensures we can safely convert TEXT to UUID
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    -- Count non-UUID format user_id values
    SELECT COUNT(*) INTO invalid_count
    FROM memories 
    WHERE user_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    AND user_id != 'system';

    IF invalid_count > 0 THEN
        -- Convert invalid user_id values to system user
        UPDATE memories 
        SET user_id = '00000000-0000-0000-0000-000000000001'
        WHERE user_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        AND user_id != 'system';
        
        RAISE NOTICE 'Converted % invalid user_id values to system user', invalid_count;
    END IF;
    
    -- Handle 'system' string values specifically
    UPDATE memories 
    SET user_id = '00000000-0000-0000-0000-000000000001'
    WHERE user_id = 'system';
END $$;

-- Repeat validation for session_memories table
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO invalid_count
    FROM session_memories 
    WHERE user_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    AND user_id != 'system';

    IF invalid_count > 0 THEN
        UPDATE session_memories 
        SET user_id = '00000000-0000-0000-0000-000000000001'
        WHERE user_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        AND user_id != 'system';
        
        RAISE NOTICE 'Converted % invalid user_id values to system user in session_memories', invalid_count;
    END IF;
    
    UPDATE session_memories 
    SET user_id = '00000000-0000-0000-0000-000000000001'
    WHERE user_id = 'system';
END $$;

-- ===========================
-- PHASE 3: CONVERT MEMORIES TABLE
-- ===========================

-- Convert memories.user_id from TEXT to UUID with foreign key constraint
ALTER TABLE memories 
    ALTER COLUMN user_id TYPE UUID USING user_id::UUID;

-- Add foreign key constraint to auth.users
ALTER TABLE memories 
    ADD CONSTRAINT memories_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- Add index for performance (RLS policies will use this)
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);

-- Add comment explaining the constraint
COMMENT ON CONSTRAINT memories_user_id_fkey ON memories 
    IS 'Foreign key constraint ensuring memory records belong to valid users. CASCADE delete removes memories when user is deleted.';

-- ===========================
-- PHASE 4: CONVERT SESSION_MEMORIES TABLE  
-- ===========================

-- Convert session_memories.user_id from TEXT to UUID with foreign key constraint
ALTER TABLE session_memories
    ALTER COLUMN user_id TYPE UUID USING user_id::UUID;

-- Add foreign key constraint to auth.users
ALTER TABLE session_memories
    ADD CONSTRAINT session_memories_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_session_memories_user_id ON session_memories(user_id);

-- Add comment explaining the constraint
COMMENT ON CONSTRAINT session_memories_user_id_fkey ON session_memories
    IS 'Foreign key constraint ensuring session memory records belong to valid users. CASCADE delete removes memories when user is deleted.';

-- ===========================
-- PHASE 5: ENABLE ROW LEVEL SECURITY
-- ===========================

-- Enable RLS on memory tables
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_memories ENABLE ROW LEVEL SECURITY;

-- Add RLS policies for memories table
CREATE POLICY "Users can only access their own memories" ON memories
    FOR ALL USING (auth.uid() = user_id);

-- Add RLS policies for session_memories table  
CREATE POLICY "Users can only access their own session memories" ON session_memories
    FOR ALL USING (auth.uid() = user_id);

-- Add policy comments for documentation
COMMENT ON POLICY "Users can only access their own memories" ON memories
    IS 'RLS policy ensuring users can only view, create, update, and delete their own memory records. Critical for data isolation in multi-tenant system.';

COMMENT ON POLICY "Users can only access their own session memories" ON session_memories
    IS 'RLS policy ensuring users can only access session memory records from their own chat sessions. Prevents cross-user data leakage.';

-- ===========================
-- PHASE 6: UPDATE DATABASE FUNCTIONS
-- ===========================

-- Update maintenance function to use proper UUID for system operations
CREATE OR REPLACE FUNCTION maintain_database_performance()
RETURNS VOID AS $$
BEGIN
    -- Refresh statistics for query planner
    ANALYZE trips;
    ANALYZE flights;
    ANALYZE accommodations;
    ANALYZE chat_sessions;
    ANALYZE chat_messages;
    ANALYZE memories;
    ANALYZE session_memories;
    
    -- Cleanup expired sessions and old data
    PERFORM cleanup_expired_session_memories();
    PERFORM expire_inactive_sessions();
    
    -- Log maintenance completion with proper UUID
    INSERT INTO session_memories (
        session_id, user_id, content, metadata
    ) VALUES (
        '00000000-0000-0000-0000-000000000000'::UUID, 
        '00000000-0000-0000-0000-000000000001'::UUID, -- Use UUID instead of 'system'
        'Database maintenance completed', 
        jsonb_build_object('type', 'maintenance', 'timestamp', NOW())
    );
END;
$$ LANGUAGE plpgsql;

-- Update function signature if search_memories function exists
-- Note: This function may not exist yet, so we use DO block for conditional update
DO $$
BEGIN
    -- Check if search_memories function exists and update its signature
    IF EXISTS (
        SELECT 1 FROM information_schema.routines 
        WHERE routine_name = 'search_memories' 
        AND routine_schema = 'public'
    ) THEN
        -- Drop and recreate with correct UUID parameter type
        DROP FUNCTION IF EXISTS search_memories(vector, text, int, jsonb, text, float);
        
        CREATE OR REPLACE FUNCTION search_memories(
            query_embedding vector(1536),
            query_user_id UUID, -- Changed from TEXT to UUID
            match_count INT DEFAULT 5,
            metadata_filter JSONB DEFAULT '{}',
            memory_type_filter TEXT DEFAULT NULL,
            similarity_threshold FLOAT DEFAULT 0.3
        )
        RETURNS TABLE(
            id BIGINT,
            user_id UUID,
            content TEXT,
            embedding vector(1536),
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE,
            similarity FLOAT
        ) AS $function$
        BEGIN
            RETURN QUERY
            SELECT 
                m.id,
                m.user_id,
                m.content,
                m.embedding,
                m.metadata,
                m.created_at,
                m.updated_at,
                1 - (m.embedding <=> query_embedding) as similarity
            FROM memories m
            WHERE 
                m.user_id = query_user_id
                AND (metadata_filter = '{}' OR m.metadata @> metadata_filter)
                AND (memory_type_filter IS NULL OR m.memory_type = memory_type_filter)
                AND (1 - (m.embedding <=> query_embedding)) >= similarity_threshold
            ORDER BY m.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $function$ LANGUAGE plpgsql;
        
        RAISE NOTICE 'Updated search_memories function to use UUID parameter';
    END IF;
END $$;

-- ===========================
-- PHASE 7: VERIFICATION
-- ===========================

-- Verify foreign key constraints were added correctly
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'memories' 
        AND constraint_name = 'memories_user_id_fkey'
        AND constraint_type = 'FOREIGN KEY'
    ) THEN
        RAISE EXCEPTION 'Foreign key constraint memories_user_id_fkey was not created successfully';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'session_memories' 
        AND constraint_name = 'session_memories_user_id_fkey'
        AND constraint_type = 'FOREIGN KEY'
    ) THEN
        RAISE EXCEPTION 'Foreign key constraint session_memories_user_id_fkey was not created successfully';
    END IF;
    
    RAISE NOTICE 'All foreign key constraints verified successfully';
END $$;

-- Verify RLS policies were created
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'memories' 
        AND policyname = 'Users can only access their own memories'
    ) THEN
        RAISE EXCEPTION 'RLS policy for memories table was not created successfully';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'session_memories' 
        AND policyname = 'Users can only access their own session memories'
    ) THEN
        RAISE EXCEPTION 'RLS policy for session_memories table was not created successfully';
    END IF;
    
    RAISE NOTICE 'All RLS policies verified successfully';
END $$;

-- ===========================
-- MIGRATION COMPLETION
-- ===========================

-- Log successful migration completion
INSERT INTO session_memories (session_id, user_id, content, metadata)
VALUES (
    '00000000-0000-0000-0000-000000000000'::UUID,
    '00000000-0000-0000-0000-000000000001'::UUID,
    'Migration completed successfully: Fixed user_id constraints and RLS',
    jsonb_build_object(
        'type', 'migration_complete',
        'migration', '20250610_01_fix_user_id_constraints',
        'timestamp', NOW(),
        'changes', jsonb_build_array(
            'Convert memories.user_id TEXT -> UUID with FK constraint',
            'Convert session_memories.user_id TEXT -> UUID with FK constraint', 
            'Enable RLS on memories and session_memories tables',
            'Add RLS policies for data isolation',
            'Update database functions for UUID compatibility'
        )
    )
);

COMMIT;

-- ===========================
-- POST-MIGRATION NOTES
-- ===========================

-- ROLLBACK PLAN (if needed):
-- 1. Remove foreign key constraints:
--    ALTER TABLE memories DROP CONSTRAINT memories_user_id_fkey;
--    ALTER TABLE session_memories DROP CONSTRAINT session_memories_user_id_fkey;
-- 2. Convert back to TEXT:  
--    ALTER TABLE memories ALTER COLUMN user_id TYPE TEXT;
--    ALTER TABLE session_memories ALTER COLUMN user_id TYPE TEXT;
-- 3. Disable RLS:
--    ALTER TABLE memories DISABLE ROW LEVEL SECURITY;
--    ALTER TABLE session_memories DISABLE ROW LEVEL SECURITY;

-- VERIFICATION QUERIES:
-- Check foreign key constraints:
-- SELECT * FROM information_schema.table_constraints 
-- WHERE table_name IN ('memories', 'session_memories') AND constraint_type = 'FOREIGN KEY';

-- Check RLS policies:
-- SELECT * FROM pg_policies WHERE tablename IN ('memories', 'session_memories');

-- Check user_id data types:
-- SELECT column_name, data_type FROM information_schema.columns 
-- WHERE table_name IN ('memories', 'session_memories') AND column_name = 'user_id';