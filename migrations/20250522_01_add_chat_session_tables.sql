-- Migration: Add Chat Session Tables
-- Description: Creates tables for chat session management and message history
-- Created: 2025-05-22

-- Create chat_sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    
    -- Indexes for performance
    CONSTRAINT chat_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create index on user_id for efficient lookups
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_created_at ON chat_sessions(created_at DESC);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);

COMMENT ON TABLE chat_sessions IS 'Chat sessions for tracking conversations with AI assistant';
COMMENT ON COLUMN chat_sessions.id IS 'Unique identifier for the chat session (UUID)';
COMMENT ON COLUMN chat_sessions.user_id IS 'Reference to the user who owns this session';
COMMENT ON COLUMN chat_sessions.created_at IS 'When the session was created';
COMMENT ON COLUMN chat_sessions.updated_at IS 'When the session was last active';
COMMENT ON COLUMN chat_sessions.ended_at IS 'When the session was explicitly ended (null if active)';
COMMENT ON COLUMN chat_sessions.metadata IS 'Additional session metadata (e.g., context settings, preferences)';

-- Create chat_messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT chat_messages_role_check CHECK (role IN ('user', 'assistant', 'system')),
    CONSTRAINT chat_messages_content_length CHECK (length(content) <= 32768)
);

-- Create indexes for efficient querying
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(session_id, created_at DESC);
CREATE INDEX idx_chat_messages_role ON chat_messages(session_id, role);

COMMENT ON TABLE chat_messages IS 'Individual messages within chat sessions';
COMMENT ON COLUMN chat_messages.id IS 'Unique identifier for the message';
COMMENT ON COLUMN chat_messages.session_id IS 'Reference to the chat session';
COMMENT ON COLUMN chat_messages.role IS 'Role of the message sender (user, assistant, system)';
COMMENT ON COLUMN chat_messages.content IS 'The actual message content (limited to 32KB)';
COMMENT ON COLUMN chat_messages.created_at IS 'When the message was created';
COMMENT ON COLUMN chat_messages.metadata IS 'Additional metadata (e.g., tool calls, token usage, model info)';

-- Create chat_tool_calls table for tracking tool usage
CREATE TABLE IF NOT EXISTS chat_tool_calls (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    tool_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments JSONB NOT NULL DEFAULT '{}',
    result JSONB,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    
    -- Constraints
    CONSTRAINT chat_tool_calls_status_check CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

-- Create indexes for tool calls
CREATE INDEX idx_chat_tool_calls_message_id ON chat_tool_calls(message_id);
CREATE INDEX idx_chat_tool_calls_status ON chat_tool_calls(status);
CREATE INDEX idx_chat_tool_calls_tool_name ON chat_tool_calls(tool_name);

COMMENT ON TABLE chat_tool_calls IS 'Tool calls made during chat conversations';
COMMENT ON COLUMN chat_tool_calls.id IS 'Unique identifier for the tool call';
COMMENT ON COLUMN chat_tool_calls.message_id IS 'Reference to the message that triggered this tool call';
COMMENT ON COLUMN chat_tool_calls.tool_id IS 'Unique identifier for the specific tool call instance';
COMMENT ON COLUMN chat_tool_calls.tool_name IS 'Name of the tool that was called';
COMMENT ON COLUMN chat_tool_calls.arguments IS 'Arguments passed to the tool';
COMMENT ON COLUMN chat_tool_calls.result IS 'Result returned by the tool (if successful)';
COMMENT ON COLUMN chat_tool_calls.status IS 'Current status of the tool call';
COMMENT ON COLUMN chat_tool_calls.created_at IS 'When the tool call was initiated';
COMMENT ON COLUMN chat_tool_calls.completed_at IS 'When the tool call completed (success or failure)';
COMMENT ON COLUMN chat_tool_calls.error_message IS 'Error message if the tool call failed';

-- Update trigger for chat_sessions
CREATE TRIGGER update_chat_sessions_updated_at
BEFORE UPDATE ON chat_sessions
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Create function to get recent messages with context window management
CREATE OR REPLACE FUNCTION get_recent_messages(
    p_session_id UUID,
    p_limit INTEGER DEFAULT 10,
    p_max_tokens INTEGER DEFAULT 8000
) RETURNS TABLE (
    id BIGINT,
    role TEXT,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    estimated_tokens INTEGER
) AS $$
DECLARE
    v_total_tokens INTEGER := 0;
    v_message RECORD;
BEGIN
    -- Estimate tokens as roughly 4 characters per token (conservative estimate)
    -- Return most recent messages that fit within token limit
    FOR v_message IN 
        SELECT 
            m.id,
            m.role,
            m.content,
            m.created_at,
            m.metadata,
            CEIL(LENGTH(m.content) / 4.0)::INTEGER as estimated_tokens
        FROM chat_messages m
        WHERE m.session_id = p_session_id
        ORDER BY m.created_at DESC
        LIMIT p_limit
    LOOP
        -- Check if adding this message would exceed token limit
        IF v_total_tokens + v_message.estimated_tokens > p_max_tokens THEN
            EXIT;
        END IF;
        
        v_total_tokens := v_total_tokens + v_message.estimated_tokens;
        
        RETURN QUERY SELECT 
            v_message.id,
            v_message.role,
            v_message.content,
            v_message.created_at,
            v_message.metadata,
            v_message.estimated_tokens;
    END LOOP;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_recent_messages IS 'Retrieves recent messages from a session with context window management';

-- Create view for active sessions
CREATE OR REPLACE VIEW active_chat_sessions AS
SELECT 
    cs.id,
    cs.user_id,
    cs.created_at,
    cs.updated_at,
    cs.metadata,
    COUNT(cm.id) as message_count,
    MAX(cm.created_at) as last_message_at
FROM chat_sessions cs
LEFT JOIN chat_messages cm ON cs.id = cm.session_id
WHERE cs.ended_at IS NULL
GROUP BY cs.id, cs.user_id, cs.created_at, cs.updated_at, cs.metadata;

COMMENT ON VIEW active_chat_sessions IS 'View of currently active chat sessions with message statistics';

-- Create function to clean up old sessions (optional, for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_sessions(p_days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM chat_sessions
        WHERE updated_at < NOW() - INTERVAL '1 day' * p_days_old
        AND ended_at IS NOT NULL
        RETURNING 1
    )
    SELECT COUNT(*) INTO v_deleted_count FROM deleted;
    
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_sessions IS 'Removes old ended sessions for maintenance';