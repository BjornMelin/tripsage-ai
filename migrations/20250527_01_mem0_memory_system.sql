-- Mem0 Memory System Migration
-- Replace Neo4j-based memory with Mem0 + pgvector implementation
-- Based on research from docs/REFACTOR/MEMORY_SEARCH/RESEARCH_DB_MEMORY_SEARCH.md

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop old memory-related tables if they exist (complete replacement)
DROP TABLE IF EXISTS user_memories CASCADE;
DROP TABLE IF EXISTS trip_memories CASCADE;
DROP TABLE IF EXISTS session_memories CASCADE;

-- Create optimized memories table for Mem0
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    memory TEXT NOT NULL,
    embedding vector(1536), -- OpenAI text-embedding-3-small dimensions
    metadata JSONB DEFAULT '{}',
    categories TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    version INT DEFAULT 1,
    hash TEXT, -- For deduplication
    relevance_score FLOAT DEFAULT 1.0
);

-- Create optimized indexes for performance
CREATE INDEX idx_memories_user_id ON memories(user_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_memories_metadata ON memories USING GIN(metadata) WHERE is_deleted = FALSE;
CREATE INDEX idx_memories_categories ON memories USING GIN(categories) WHERE is_deleted = FALSE;
CREATE INDEX idx_memories_created_at ON memories(created_at DESC) WHERE is_deleted = FALSE;
CREATE INDEX idx_memories_hash ON memories(hash) WHERE is_deleted = FALSE;

-- Create vector similarity index with pgvectorscale (research shows 11x performance improvement)
CREATE INDEX memories_embedding_idx ON memories 
USING diskann (embedding vector_cosine_ops)
WHERE is_deleted = FALSE;

-- Function for optimized hybrid search (vector + metadata + text)
CREATE OR REPLACE FUNCTION search_memories(
    query_embedding vector(1536),
    query_user_id TEXT,
    match_count INT DEFAULT 5,
    metadata_filter JSONB DEFAULT '{}',
    category_filter TEXT[] DEFAULT '{}',
    similarity_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    memory TEXT,
    metadata JSONB,
    categories TEXT[],
    similarity FLOAT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.memory,
        m.metadata,
        m.categories,
        1 - (m.embedding <=> query_embedding) AS similarity,
        m.created_at
    FROM memories m
    WHERE 
        m.user_id = query_user_id
        AND m.is_deleted = FALSE
        AND (1 - (m.embedding <=> query_embedding)) >= similarity_threshold
        AND (metadata_filter = '{}' OR m.metadata @> metadata_filter)
        AND (array_length(category_filter, 1) IS NULL OR m.categories && category_filter)
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function for memory deduplication (prevents duplicate memories)
CREATE OR REPLACE FUNCTION deduplicate_memories()
RETURNS TRIGGER AS $$
DECLARE
    existing_id UUID;
    similarity_score FLOAT;
BEGIN
    -- Check for similar memories using both hash and vector similarity
    SELECT 
        id,
        1 - (embedding <=> NEW.embedding) AS sim_score
    INTO existing_id, similarity_score
    FROM memories
    WHERE user_id = NEW.user_id
    AND is_deleted = FALSE
    AND (
        hash = NEW.hash OR  -- Exact content match
        (embedding <=> NEW.embedding) < 0.05  -- 95% similarity threshold
    )
    AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::UUID)
    ORDER BY embedding <=> NEW.embedding
    LIMIT 1;
    
    -- If similar memory found, update instead of creating duplicate
    IF existing_id IS NOT NULL THEN
        UPDATE memories
        SET 
            memory = CASE 
                WHEN similarity_score > 0.98 THEN NEW.memory  -- Very similar, replace
                ELSE memory || ' | ' || NEW.memory  -- Somewhat similar, append
            END,
            metadata = metadata || NEW.metadata,
            categories = array(SELECT DISTINCT unnest(categories || NEW.categories)),
            updated_at = NOW(),
            version = version + 1,
            relevance_score = GREATEST(relevance_score, NEW.relevance_score)
        WHERE id = existing_id;
        
        RETURN NULL;  -- Prevent insert
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create deduplication trigger
CREATE TRIGGER deduplicate_memories_trigger
BEFORE INSERT ON memories
FOR EACH ROW
EXECUTE FUNCTION deduplicate_memories();

-- Function to clean up old/unused memories (memory decay)
CREATE OR REPLACE FUNCTION cleanup_old_memories(
    days_old INT DEFAULT 365,
    max_memories_per_user INT DEFAULT 1000
)
RETURNS INT AS $$
DECLARE
    deleted_count INT := 0;
BEGIN
    -- Mark very old memories as deleted
    UPDATE memories 
    SET is_deleted = TRUE, updated_at = NOW()
    WHERE created_at < NOW() - INTERVAL '1 day' * days_old
    AND is_deleted = FALSE;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Keep only the most recent memories per user if exceeding limit
    WITH ranked_memories AS (
        SELECT id, ROW_NUMBER() OVER (
            PARTITION BY user_id 
            ORDER BY created_at DESC, relevance_score DESC
        ) as rn
        FROM memories 
        WHERE is_deleted = FALSE
    )
    UPDATE memories 
    SET is_deleted = TRUE, updated_at = NOW()
    WHERE id IN (
        SELECT id FROM ranked_memories WHERE rn > max_memories_per_user
    );
    
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create session memories table for conversation context
CREATE TABLE session_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    message_index INT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

-- Indexes for session memories
CREATE INDEX idx_session_memories_session_id ON session_memories(session_id);
CREATE INDEX idx_session_memories_user_id ON session_memories(user_id);
CREATE INDEX idx_session_memories_expires_at ON session_memories(expires_at);

-- Function to clean up expired session memories
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM session_memories 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create travel-specific memory views for common queries
CREATE VIEW user_travel_preferences AS
SELECT 
    user_id,
    jsonb_agg(DISTINCT jsonb_extract_path_text(metadata, 'preference_type')) FILTER (WHERE jsonb_extract_path_text(metadata, 'preference_type') IS NOT NULL) as preference_types,
    jsonb_agg(DISTINCT jsonb_extract_path_text(metadata, 'destination')) FILTER (WHERE jsonb_extract_path_text(metadata, 'destination') IS NOT NULL) as preferred_destinations,
    jsonb_agg(DISTINCT jsonb_extract_path_text(metadata, 'activity')) FILTER (WHERE jsonb_extract_path_text(metadata, 'activity') IS NOT NULL) as preferred_activities,
    COUNT(*) as total_memories,
    MAX(created_at) as last_updated
FROM memories 
WHERE is_deleted = FALSE 
AND 'travel_preferences' = ANY(categories)
GROUP BY user_id;

-- Performance optimization: Periodic maintenance function
CREATE OR REPLACE FUNCTION maintain_memory_performance()
RETURNS VOID AS $$
BEGIN
    -- Refresh statistics for query planner
    ANALYZE memories;
    ANALYZE session_memories;
    
    -- Cleanup expired sessions
    PERFORM cleanup_expired_sessions();
    
    -- Cleanup old memories (run monthly)
    PERFORM cleanup_old_memories();
    
    -- Log maintenance completion
    INSERT INTO session_memories (
        session_id, user_id, message_index, role, content, metadata
    ) VALUES (
        'system_maintenance', 'system', 0, 'system', 
        'Memory system maintenance completed', 
        jsonb_build_object('type', 'maintenance', 'timestamp', NOW())
    );
END;
$$ LANGUAGE plpgsql;

-- Grant appropriate permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON memories TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON session_memories TO authenticated;
GRANT SELECT ON user_travel_preferences TO authenticated;

-- Add helpful comments
COMMENT ON TABLE memories IS 'Mem0-based memory storage with pgvector for semantic search';
COMMENT ON COLUMN memories.embedding IS 'OpenAI text-embedding-3-small (1536 dimensions)';
COMMENT ON COLUMN memories.hash IS 'Content hash for deduplication';
COMMENT ON INDEX memories_embedding_idx IS 'pgvectorscale DiskANN index for 11x performance improvement';

COMMENT ON TABLE session_memories IS 'Temporary conversation context storage';
COMMENT ON FUNCTION search_memories IS 'Optimized hybrid search: vector similarity + metadata + categories';
COMMENT ON FUNCTION deduplicate_memories IS 'Prevents duplicate memories via hash and vector similarity';