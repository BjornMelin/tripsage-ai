-- Database Functions Schema
-- Description: Utility functions and stored procedures for TripSage database
-- Dependencies: 01_tables.sql (table definitions)

-- ===========================
-- UTILITY FUNCTIONS
-- ===========================

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- MEMORY SYSTEM FUNCTIONS
-- ===========================

-- Function for optimized hybrid search (vector + metadata filtering)
CREATE OR REPLACE FUNCTION search_memories(
    query_embedding vector(1536),
    query_user_id TEXT,
    match_count INT DEFAULT 5,
    metadata_filter JSONB DEFAULT '{}',
    memory_type_filter TEXT DEFAULT NULL,
    similarity_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    memory_type TEXT,
    similarity FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.content,
        m.metadata,
        m.memory_type,
        1 - (m.embedding <=> query_embedding) AS similarity,
        m.created_at
    FROM memories m
    WHERE 
        m.user_id = query_user_id
        AND (1 - (m.embedding <=> query_embedding)) >= similarity_threshold
        AND (metadata_filter = '{}' OR m.metadata @> metadata_filter)
        AND (memory_type_filter IS NULL OR m.memory_type = memory_type_filter)
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function for session memory search
CREATE OR REPLACE FUNCTION search_session_memories(
    query_embedding vector(1536),
    query_session_id UUID,
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sm.id,
        sm.content,
        sm.metadata,
        1 - (sm.embedding <=> query_embedding) AS similarity,
        sm.created_at
    FROM session_memories sm
    WHERE 
        sm.session_id = query_session_id
        AND (1 - (sm.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY sm.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to clean up old memories (maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_memories(
    days_old INT DEFAULT 365,
    max_memories_per_user INT DEFAULT 1000
)
RETURNS INT AS $$
DECLARE
    deleted_count INT := 0;
BEGIN
    -- Delete very old memories
    DELETE FROM memories 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Keep only the most recent memories per user if exceeding limit
    WITH ranked_memories AS (
        SELECT id, ROW_NUMBER() OVER (
            PARTITION BY user_id 
            ORDER BY created_at DESC
        ) as rn
        FROM memories 
    )
    DELETE FROM memories 
    WHERE id IN (
        SELECT id FROM ranked_memories WHERE rn > max_memories_per_user
    );
    
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired session memories
CREATE OR REPLACE FUNCTION cleanup_expired_session_memories(
    hours_old INT DEFAULT 24
)
RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM session_memories 
    WHERE created_at < NOW() - INTERVAL '1 hour' * hours_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- CHAT SESSION FUNCTIONS
-- ===========================

-- Function to get recent messages with context window management
CREATE OR REPLACE FUNCTION get_recent_messages(
    p_session_id UUID,
    p_limit INTEGER DEFAULT 10,
    p_max_tokens INTEGER DEFAULT 8000,
    p_offset INTEGER DEFAULT 0,
    p_chars_per_token INTEGER DEFAULT 4
) RETURNS TABLE (
    id BIGINT,
    role TEXT,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    estimated_tokens INTEGER,
    total_messages BIGINT
) AS $$
DECLARE
    v_total_tokens INTEGER := 0;
    v_message RECORD;
    v_messages RECORD[];
    v_total_messages BIGINT;
BEGIN
    -- Get total message count for pagination info
    SELECT COUNT(*) INTO v_total_messages
    FROM chat_messages
    WHERE session_id = p_session_id;

    -- Estimate tokens using configurable chars per token
    -- Collect messages that fit within token limit
    FOR v_message IN 
        SELECT 
            m.id,
            m.role,
            m.content,
            m.created_at,
            m.metadata,
            LEAST(
                CEIL(LENGTH(m.content)::FLOAT / p_chars_per_token)::INTEGER,
                p_max_tokens  -- Cap single message tokens at max
            ) as estimated_tokens
        FROM chat_messages m
        WHERE m.session_id = p_session_id
        ORDER BY m.created_at DESC
        LIMIT p_limit OFFSET p_offset
    LOOP
        -- Check if adding this message would exceed token limit
        IF v_total_tokens + v_message.estimated_tokens > p_max_tokens THEN
            -- If this is the first message and it exceeds limit, include it partially
            IF v_total_tokens = 0 THEN
                v_messages := ARRAY[v_message];
            END IF;
            EXIT;
        END IF;
        
        v_total_tokens := v_total_tokens + v_message.estimated_tokens;
        v_messages := v_message || v_messages; -- Prepend to maintain chronological order
    END LOOP;
    
    -- Return messages in chronological order (oldest first)
    FOREACH v_message IN ARRAY v_messages
    LOOP
        RETURN QUERY SELECT 
            v_message.id,
            v_message.role,
            v_message.content,
            v_message.created_at,
            v_message.metadata,
            v_message.estimated_tokens,
            v_total_messages;
    END LOOP;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- Function to expire inactive sessions
CREATE OR REPLACE FUNCTION expire_inactive_sessions(p_hours_inactive INTEGER DEFAULT 24)
RETURNS INTEGER AS $$
DECLARE
    v_expired_count INTEGER;
BEGIN
    WITH expired AS (
        UPDATE chat_sessions
        SET ended_at = NOW()
        WHERE ended_at IS NULL
        AND updated_at < NOW() - INTERVAL '1 hour' * p_hours_inactive
        RETURNING 1
    )
    SELECT COUNT(*) INTO v_expired_count FROM expired;
    
    RETURN v_expired_count;
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- MAINTENANCE FUNCTIONS
-- ===========================

-- Performance optimization: Periodic maintenance function
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
    
    -- Log maintenance completion
    INSERT INTO session_memories (
        session_id, user_id, content, metadata
    ) VALUES (
        '00000000-0000-0000-0000-000000000000'::UUID, 
        'system', 
        'Database maintenance completed', 
        jsonb_build_object('type', 'maintenance', 'timestamp', NOW())
    );
END;
$$ LANGUAGE plpgsql;