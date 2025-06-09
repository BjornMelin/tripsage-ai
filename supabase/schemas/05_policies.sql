-- Row Level Security (RLS) Policies Schema
-- Description: Multi-tenant security policies for user data isolation
-- Dependencies: 01_tables.sql (all table definitions)

-- ===========================
-- ENABLE RLS ON USER-OWNED TABLES
-- ===========================

-- Enable RLS on all tables containing user-specific data
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Enable RLS on related tables (inherit access through foreign keys)
ALTER TABLE flights ENABLE ROW LEVEL SECURITY;
ALTER TABLE accommodations ENABLE ROW LEVEL SECURITY;
ALTER TABLE transportation ENABLE ROW LEVEL SECURITY;
ALTER TABLE itinerary_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_tool_calls ENABLE ROW LEVEL SECURITY;

-- ===========================
-- CORE TABLE POLICIES
-- ===========================

-- Trips: Users can only access their own trips
CREATE POLICY "Users can only access their own trips" ON trips
    FOR ALL USING (auth.uid() = user_id);

-- Chat sessions: Users can only access their own chat sessions
CREATE POLICY "Users can only access their own chat sessions" ON chat_sessions
    FOR ALL USING (auth.uid() = user_id);

-- API keys: Users can only access their own API keys
CREATE POLICY "Users can only access their own API keys" ON api_keys
    FOR ALL USING (auth.uid() = user_id);

-- ===========================
-- RELATED TABLE POLICIES
-- ===========================

-- Flights: Users can access flights for their trips
CREATE POLICY "Users can access flights for their trips" ON flights
    FOR ALL USING (trip_id IN (SELECT id FROM trips WHERE user_id = auth.uid()));

-- Accommodations: Users can access accommodations for their trips
CREATE POLICY "Users can access accommodations for their trips" ON accommodations
    FOR ALL USING (trip_id IN (SELECT id FROM trips WHERE user_id = auth.uid()));

-- Transportation: Users can access transportation for their trips
CREATE POLICY "Users can access transportation for their trips" ON transportation
    FOR ALL USING (trip_id IN (SELECT id FROM trips WHERE user_id = auth.uid()));

-- Itinerary items: Users can access itinerary items for their trips
CREATE POLICY "Users can access itinerary items for their trips" ON itinerary_items
    FOR ALL USING (trip_id IN (SELECT id FROM trips WHERE user_id = auth.uid()));

-- ===========================
-- CHAT SYSTEM POLICIES
-- ===========================

-- Chat messages: Users can access messages in their chat sessions
CREATE POLICY "Users can access messages in their chat sessions" ON chat_messages
    FOR ALL USING (session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid()));

-- Chat tool calls: Users can access tool calls in their messages
CREATE POLICY "Users can access tool calls in their messages" ON chat_tool_calls
    FOR ALL USING (message_id IN (
        SELECT cm.id FROM chat_messages cm 
        JOIN chat_sessions cs ON cm.session_id = cs.id 
        WHERE cs.user_id = auth.uid()
    ));

-- ===========================
-- POLICY COMMENTS
-- ===========================

COMMENT ON POLICY "Users can only access their own trips" ON trips 
    IS 'RLS policy ensuring users can only view and modify their own travel trips';

COMMENT ON POLICY "Users can only access their own chat sessions" ON chat_sessions 
    IS 'RLS policy ensuring users can only access their own chat sessions and conversation history';

COMMENT ON POLICY "Users can only access their own API keys" ON api_keys 
    IS 'RLS policy ensuring users can only manage their own API keys (BYOK - Bring Your Own Keys)';

-- Note: Memory tables (memories, session_memories) do not have RLS policies
-- as they use TEXT user_id fields that require application-level filtering
-- rather than Supabase auth.uid() matching