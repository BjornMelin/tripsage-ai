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
    -- Refresh statistics for query planner (including new trip_collaborators table)
    ANALYZE trips;
    ANALYZE flights;
    ANALYZE accommodations;
    ANALYZE transportation;
    ANALYZE itinerary_items;
    ANALYZE trip_collaborators;
    ANALYZE chat_sessions;
    ANALYZE chat_messages;
    ANALYZE chat_tool_calls;
    ANALYZE api_keys;
    ANALYZE memories;
    ANALYZE session_memories;
    
    -- Cleanup expired sessions and old data
    PERFORM cleanup_expired_session_memories();
    PERFORM expire_inactive_sessions();
    
    -- Optimize vector indexes
    PERFORM optimize_vector_indexes();
    
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

-- ===========================
-- TRIP COLLABORATION FUNCTIONS
-- ===========================

-- Function to get user's accessible trips (owned + shared)
CREATE OR REPLACE FUNCTION get_user_accessible_trips(
    p_user_id UUID,
    p_include_role BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    trip_id BIGINT,
    name TEXT,
    start_date DATE,
    end_date DATE,
    destination TEXT,
    budget NUMERIC,
    travelers INTEGER,
    status TEXT,
    trip_type TEXT,
    user_role TEXT,
    permission_level TEXT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    -- Owned trips
    SELECT 
        t.id AS trip_id,
        t.name,
        t.start_date,
        t.end_date,
        t.destination,
        t.budget,
        t.travelers,
        t.status,
        t.trip_type,
        'owner' AS user_role,
        'admin' AS permission_level,
        t.created_at
    FROM trips t
    WHERE t.user_id = p_user_id
    
    UNION ALL
    
    -- Shared trips (via collaborators)
    SELECT 
        t.id AS trip_id,
        t.name,
        t.start_date,
        t.end_date,
        t.destination,
        t.budget,
        t.travelers,
        t.status,
        t.trip_type,
        'collaborator' AS user_role,
        tc.permission_level,
        t.created_at
    FROM trips t
    JOIN trip_collaborators tc ON t.id = tc.trip_id
    WHERE tc.user_id = p_user_id
    
    ORDER BY created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to check user permissions for a trip
CREATE OR REPLACE FUNCTION check_trip_permission(
    p_user_id UUID,
    p_trip_id BIGINT,
    p_required_permission TEXT DEFAULT 'view'
)
RETURNS BOOLEAN AS $$
DECLARE
    v_user_permission TEXT;
    v_permission_hierarchy INT;
    v_required_hierarchy INT;
BEGIN
    -- Get user's highest permission level for the trip
    SELECT 
        CASE 
            WHEN t.user_id = p_user_id THEN 'admin'
            ELSE COALESCE(tc.permission_level, 'none')
        END INTO v_user_permission
    FROM trips t
    LEFT JOIN trip_collaborators tc ON t.id = tc.trip_id AND tc.user_id = p_user_id
    WHERE t.id = p_trip_id
    LIMIT 1;
    
    -- Permission hierarchy: view(1) < edit(2) < admin(3)
    v_permission_hierarchy := CASE v_user_permission
        WHEN 'view' THEN 1
        WHEN 'edit' THEN 2
        WHEN 'admin' THEN 3
        ELSE 0
    END;
    
    v_required_hierarchy := CASE p_required_permission
        WHEN 'view' THEN 1
        WHEN 'edit' THEN 2
        WHEN 'admin' THEN 3
        ELSE 1
    END;
    
    RETURN v_permission_hierarchy >= v_required_hierarchy;
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- VECTOR INDEX OPTIMIZATION
-- ===========================

-- Function to optimize vector indexes for better performance
CREATE OR REPLACE FUNCTION optimize_vector_indexes()
RETURNS TEXT AS $$
DECLARE
    v_memories_count BIGINT;
    v_session_memories_count BIGINT;
    v_result TEXT := '';
BEGIN
    -- Get current record counts
    SELECT COUNT(*) INTO v_memories_count FROM memories;
    SELECT COUNT(*) INTO v_session_memories_count FROM session_memories;
    
    -- Optimize memories vector index if we have significant data
    IF v_memories_count > 1000 THEN
        -- Reindex with optimized list count based on data size
        EXECUTE 'DROP INDEX IF EXISTS idx_memories_embedding';
        EXECUTE format(
            'CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = %s)',
            GREATEST(LEAST(v_memories_count / 1000, 1000), 10)
        );
        v_result := v_result || format('Optimized memories index for %s records. ', v_memories_count);
    END IF;
    
    -- Optimize session_memories vector index
    IF v_session_memories_count > 500 THEN
        EXECUTE 'DROP INDEX IF EXISTS idx_session_memories_embedding';
        EXECUTE format(
            'CREATE INDEX idx_session_memories_embedding ON session_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = %s)',
            GREATEST(LEAST(v_session_memories_count / 500, 500), 10)
        );
        v_result := v_result || format('Optimized session_memories index for %s records. ', v_session_memories_count);
    END IF;
    
    IF v_result = '' THEN
        v_result := 'No vector index optimization needed.';
    END IF;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- COLLABORATION MAINTENANCE FUNCTIONS
-- ===========================

-- Function to clean up orphaned collaboration records
CREATE OR REPLACE FUNCTION cleanup_orphaned_collaborators()
RETURNS INT AS $$
DECLARE
    v_deleted_count INT := 0;
BEGIN
    -- Remove collaborators for non-existent trips
    DELETE FROM trip_collaborators 
    WHERE trip_id NOT IN (SELECT id FROM trips);
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    -- Remove duplicate collaborations (keep the most recent)
    WITH duplicate_collaborations AS (
        SELECT id, ROW_NUMBER() OVER (
            PARTITION BY trip_id, user_id 
            ORDER BY added_at DESC
        ) as rn
        FROM trip_collaborators
    )
    DELETE FROM trip_collaborators 
    WHERE id IN (
        SELECT id FROM duplicate_collaborations WHERE rn > 1
    );
    
    GET DIAGNOSTICS v_deleted_count = v_deleted_count + ROW_COUNT;
    
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get collaboration statistics
CREATE OR REPLACE FUNCTION get_collaboration_statistics()
RETURNS TABLE (
    total_trips BIGINT,
    shared_trips BIGINT,
    total_collaborators BIGINT,
    avg_collaborators_per_trip NUMERIC,
    most_collaborative_user UUID,
    collaboration_percentage NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM trips) AS total_trips,
        (SELECT COUNT(DISTINCT trip_id) FROM trip_collaborators) AS shared_trips,
        (SELECT COUNT(*) FROM trip_collaborators) AS total_collaborators,
        (SELECT ROUND(AVG(collaborator_count), 2) FROM (
            SELECT COUNT(*) as collaborator_count 
            FROM trip_collaborators 
            GROUP BY trip_id
        ) sub) AS avg_collaborators_per_trip,
        (SELECT added_by FROM trip_collaborators 
         GROUP BY added_by 
         ORDER BY COUNT(*) DESC 
         LIMIT 1) AS most_collaborative_user,
        ROUND(
            (SELECT COUNT(DISTINCT trip_id) FROM trip_collaborators) * 100.0 / 
            NULLIF((SELECT COUNT(*) FROM trips), 0), 
            2
        ) AS collaboration_percentage;
END;
$$ LANGUAGE plpgsql;

-- Function to bulk update collaborator permissions
CREATE OR REPLACE FUNCTION bulk_update_collaborator_permissions(
    p_trip_id BIGINT,
    p_user_id UUID, -- The user making the changes (must be owner)
    p_permission_updates JSONB -- Array of {user_id, permission_level}
)
RETURNS INT AS $$
DECLARE
    v_is_owner BOOLEAN;
    v_update_count INT := 0;
    v_update JSONB;
BEGIN
    -- Check if the user is the trip owner
    SELECT user_id = p_user_id INTO v_is_owner
    FROM trips WHERE id = p_trip_id;
    
    IF NOT v_is_owner THEN
        RAISE EXCEPTION 'Only trip owners can bulk update collaborator permissions';
    END IF;
    
    -- Process each permission update
    FOR v_update IN SELECT jsonb_array_elements(p_permission_updates)
    LOOP
        UPDATE trip_collaborators 
        SET 
            permission_level = v_update->>'permission_level',
            updated_at = NOW()
        WHERE 
            trip_id = p_trip_id 
            AND user_id = (v_update->>'user_id')::UUID;
        
        GET DIAGNOSTICS v_update_count = v_update_count + ROW_COUNT;
    END LOOP;
    
    RETURN v_update_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get user activity summary for a trip
CREATE OR REPLACE FUNCTION get_trip_activity_summary(
    p_trip_id BIGINT,
    p_days_back INT DEFAULT 30
)
RETURNS TABLE (
    user_id UUID,
    permission_level TEXT,
    messages_sent BIGINT,
    last_activity TIMESTAMP WITH TIME ZONE,
    days_since_activity INT,
    is_active BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH trip_users AS (
        -- Trip owner
        SELECT t.user_id, 'admin' as permission_level
        FROM trips t WHERE t.id = p_trip_id
        UNION
        -- Collaborators
        SELECT tc.user_id, tc.permission_level
        FROM trip_collaborators tc WHERE tc.trip_id = p_trip_id
    ),
    user_activity AS (
        SELECT 
            tu.user_id,
            tu.permission_level,
            COUNT(cm.id) as messages_sent,
            MAX(cm.created_at) as last_activity
        FROM trip_users tu
        LEFT JOIN chat_sessions cs ON cs.trip_id = p_trip_id AND cs.user_id = tu.user_id
        LEFT JOIN chat_messages cm ON cm.session_id = cs.id 
            AND cm.created_at > NOW() - INTERVAL '1 day' * p_days_back
        GROUP BY tu.user_id, tu.permission_level
    )
    SELECT 
        ua.user_id,
        ua.permission_level,
        ua.messages_sent,
        ua.last_activity,
        CASE 
            WHEN ua.last_activity IS NULL THEN NULL
            ELSE EXTRACT(DAYS FROM NOW() - ua.last_activity)::INT
        END as days_since_activity,
        CASE 
            WHEN ua.last_activity IS NULL THEN FALSE
            ELSE ua.last_activity > NOW() - INTERVAL '7 days'
        END as is_active
    FROM user_activity ua
    ORDER BY ua.last_activity DESC NULLS LAST;
END;
$$ LANGUAGE plpgsql;