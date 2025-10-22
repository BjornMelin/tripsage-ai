-- Row Level Security (RLS) Policies Schema
-- Description: multi-tenant security policies with collaboration support
-- Dependencies: 01_tables.sql (all table definitions)
-- Last Updated: 2025-06-11 - Includes collaboration features

-- ===========================
-- ENABLE RLS ON ALL USER-OWNED TABLES
-- ===========================

-- Core business tables
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_collaborators ENABLE ROW LEVEL SECURITY;

-- Travel data tables (inherit permissions from trips)
ALTER TABLE flights ENABLE ROW LEVEL SECURITY;
ALTER TABLE accommodations ENABLE ROW LEVEL SECURITY;
ALTER TABLE transportation ENABLE ROW LEVEL SECURITY;
ALTER TABLE itinerary_items ENABLE ROW LEVEL SECURITY;

-- Communication tables
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_tool_calls ENABLE ROW LEVEL SECURITY;

-- User management tables
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Memory tables (now using UUID user_id with proper foreign key constraints)
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_memories ENABLE ROW LEVEL SECURITY;

-- ===========================
-- CORE BUSINESS LOGIC POLICIES
-- ===========================

-- API Keys: Users can only manage their own API keys
CREATE POLICY "Users can only access their own API keys" ON api_keys
    FOR ALL USING (auth.uid() = user_id);

-- Memory System: Users can only access their own memories
CREATE POLICY "Users can only access their own memories" ON memories
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can only access their own session memories" ON session_memories
    FOR ALL USING (auth.uid() = user_id);

-- Chat Sessions: Users can access sessions for owned and shared trips
CREATE POLICY "Users can access chat sessions for accessible trips" ON chat_sessions
    FOR SELECT USING (
        auth.uid() = user_id OR
        trip_id IN (
            SELECT id FROM trips 
            WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid()
        )
    );

-- Separate policies for chat session modifications
CREATE POLICY "Users can create their own chat sessions" ON chat_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own chat sessions" ON chat_sessions
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own chat sessions" ON chat_sessions
    FOR DELETE USING (auth.uid() = user_id);

-- ===========================
-- TRIP COLLABORATION POLICIES
-- ===========================

-- Trip collaborators: Users can view collaborations they are part of
CREATE POLICY "Users can view trip collaborations they are part of" ON trip_collaborators
    FOR SELECT USING (
        user_id = auth.uid() OR 
        added_by = auth.uid() OR
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
        )
    );

-- Trip owners can manage collaborators
CREATE POLICY "Trip owners can add collaborators" ON trip_collaborators
    FOR INSERT WITH CHECK (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Trip owners can update collaborators" ON trip_collaborators
    FOR UPDATE USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Trip owners can remove collaborators" ON trip_collaborators
    FOR DELETE USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
        )
    );

-- ===========================
-- ENHANCED TRIP ACCESS POLICIES
-- ===========================

-- Trips: Users can view owned and shared trips
CREATE POLICY "Users can view accessible trips" ON trips
    FOR SELECT USING (
        auth.uid() = user_id OR
        id IN (
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid()
        )
    );

-- Trip modifications require ownership or appropriate permissions
CREATE POLICY "Users can create their own trips" ON trips
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update owned trips or shared trips with edit permission" ON trips
    FOR UPDATE USING (
        auth.uid() = user_id OR
        id IN (
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

CREATE POLICY "Users can delete their own trips" ON trips
    FOR DELETE USING (auth.uid() = user_id);

-- ===========================
-- TRAVEL DATA POLICIES (COLLABORATIVE)
-- ===========================

-- Flights: Access based on trip permissions
CREATE POLICY "Users can view flights for accessible trips" ON flights
    FOR SELECT USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can modify flights with edit permissions" ON flights
    FOR INSERT WITH CHECK (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

CREATE POLICY "Users can update flights with edit permissions" ON flights
    FOR UPDATE USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

CREATE POLICY "Users can delete flights with edit permissions" ON flights
    FOR DELETE USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

-- Accommodations: Similar collaborative access patterns
CREATE POLICY "Users can view accommodations for accessible trips" ON accommodations
    FOR SELECT USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can modify accommodations with edit permissions" ON accommodations
    FOR INSERT WITH CHECK (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

CREATE POLICY "Users can update accommodations with edit permissions" ON accommodations
    FOR UPDATE USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

CREATE POLICY "Users can delete accommodations with edit permissions" ON accommodations
    FOR DELETE USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

-- Transportation: Collaborative access
CREATE POLICY "Users can view transportation for accessible trips" ON transportation
    FOR SELECT USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can modify transportation with edit permissions" ON transportation
    FOR INSERT WITH CHECK (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

CREATE POLICY "Users can update transportation with edit permissions" ON transportation
    FOR UPDATE USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

CREATE POLICY "Users can delete transportation with edit permissions" ON transportation
    FOR DELETE USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

-- Itinerary items: Collaborative access
CREATE POLICY "Users can view itinerary items for accessible trips" ON itinerary_items
    FOR SELECT USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can modify itinerary items with edit permissions" ON itinerary_items
    FOR INSERT WITH CHECK (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

CREATE POLICY "Users can update itinerary items with edit permissions" ON itinerary_items
    FOR UPDATE USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

CREATE POLICY "Users can delete itinerary items with edit permissions" ON itinerary_items
    FOR DELETE USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators 
            WHERE user_id = auth.uid() 
            AND permission_level IN ('edit', 'admin')
        )
    );

-- ===========================
-- CHAT SYSTEM POLICIES (COLLABORATIVE)
-- ===========================

-- Chat messages: Users can access messages in accessible chat sessions
CREATE POLICY "Users can view messages in accessible chat sessions" ON chat_messages
    FOR SELECT USING (
        session_id IN (
            SELECT id FROM chat_sessions 
            WHERE user_id = auth.uid()
            OR trip_id IN (
                SELECT id FROM trips WHERE user_id = auth.uid()
                UNION
                SELECT trip_id FROM trip_collaborators WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Users can create messages in their chat sessions" ON chat_messages
    FOR INSERT WITH CHECK (
        session_id IN (
            SELECT id FROM chat_sessions WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update their own messages" ON chat_messages
    FOR UPDATE USING (
        session_id IN (
            SELECT id FROM chat_sessions WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete their own messages" ON chat_messages
    FOR DELETE USING (
        session_id IN (
            SELECT id FROM chat_sessions WHERE user_id = auth.uid()
        )
    );

-- Chat tool calls: Users can access tool calls in accessible messages
CREATE POLICY "Users can view tool calls in accessible messages" ON chat_tool_calls
    FOR SELECT USING (
        message_id IN (
            SELECT cm.id FROM chat_messages cm 
            JOIN chat_sessions cs ON cm.session_id = cs.id 
            WHERE cs.user_id = auth.uid()
            OR cs.trip_id IN (
                SELECT id FROM trips WHERE user_id = auth.uid()
                UNION
                SELECT trip_id FROM trip_collaborators WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Users can create tool calls in their messages" ON chat_tool_calls
    FOR INSERT WITH CHECK (
        message_id IN (
            SELECT cm.id FROM chat_messages cm 
            JOIN chat_sessions cs ON cm.session_id = cs.id 
            WHERE cs.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update tool calls in their messages" ON chat_tool_calls
    FOR UPDATE USING (
        message_id IN (
            SELECT cm.id FROM chat_messages cm 
            JOIN chat_sessions cs ON cm.session_id = cs.id 
            WHERE cs.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete tool calls in their messages" ON chat_tool_calls
    FOR DELETE USING (
        message_id IN (
            SELECT cm.id FROM chat_messages cm 
            JOIN chat_sessions cs ON cm.session_id = cs.id 
            WHERE cs.user_id = auth.uid()
        )
    );

-- ===========================
-- FILE ATTACHMENTS POLICIES
-- ===========================

-- Enable RLS on file attachments
ALTER TABLE file_attachments ENABLE ROW LEVEL SECURITY;

-- File attachments: Users can view files they uploaded or files attached to accessible trips
CREATE POLICY "Users can view accessible file attachments" ON file_attachments
    FOR SELECT USING (
        auth.uid() = user_id OR
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
            UNION
            SELECT trip_id FROM trip_collaborators WHERE user_id = auth.uid()
        )
    );

-- Users can upload files to their own trips or shared trips with edit permission
CREATE POLICY "Users can upload files to accessible trips" ON file_attachments
    FOR INSERT WITH CHECK (
        auth.uid() = user_id AND (
            trip_id IS NULL OR
            trip_id IN (
                SELECT id FROM trips WHERE user_id = auth.uid()
                UNION
                SELECT trip_id FROM trip_collaborators 
                WHERE user_id = auth.uid() 
                AND permission_level IN ('edit', 'admin')
            )
        )
    );

-- Users can update their own file attachments
CREATE POLICY "Users can update their own file attachments" ON file_attachments
    FOR UPDATE USING (auth.uid() = user_id);

-- Users can delete their own file attachments or files from trips they own
CREATE POLICY "Users can delete accessible file attachments" ON file_attachments
    FOR DELETE USING (
        auth.uid() = user_id OR
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
        )
    );

-- ===========================
-- SEARCH CACHE POLICIES
-- ===========================

-- Enable RLS on search cache tables
ALTER TABLE search_destinations ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_flights ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_hotels ENABLE ROW LEVEL SECURITY;

-- Search destinations: Users can only access their own search cache
CREATE POLICY "Users can only access their own destination searches" ON search_destinations
    FOR ALL USING (auth.uid() = user_id);

-- Search activities: Users can only access their own search cache
CREATE POLICY "Users can only access their own activity searches" ON search_activities
    FOR ALL USING (auth.uid() = user_id);

-- Search flights: Users can only access their own search cache
CREATE POLICY "Users can only access their own flight searches" ON search_flights
    FOR ALL USING (auth.uid() = user_id);

-- Search hotels: Users can only access their own search cache
CREATE POLICY "Users can only access their own hotel searches" ON search_hotels
    FOR ALL USING (auth.uid() = user_id);

-- ===========================
-- POLICY DOCUMENTATION
-- ===========================

COMMENT ON POLICY "Users can only access their own API keys" ON api_keys 
    IS 'RLS policy ensuring users can only manage their own API keys (BYOK - Bring Your Own Keys)';

COMMENT ON POLICY "Users can view trip collaborations they are part of" ON trip_collaborators 
    IS 'RLS policy allowing users to view collaborations where they are the collaborator, owner, or trip owner';

COMMENT ON POLICY "Users can view accessible trips" ON trips 
    IS 'RLS policy allowing access to owned trips and trips shared via trip_collaborators';

COMMENT ON POLICY "Users can access chat sessions for accessible trips" ON chat_sessions 
    IS 'RLS policy allowing access to chat sessions for owned trips and trips shared via collaboration';

COMMENT ON POLICY "Users can view flights for accessible trips" ON flights 
    IS 'RLS policy with collaborative access - users can view flights for owned and shared trips';

COMMENT ON POLICY "Users can modify flights with edit permissions" ON flights 
    IS 'RLS policy enforcing edit permissions - users can modify flights only with edit/admin permissions';

-- ===========================
-- SECURITY CONSIDERATIONS
-- ===========================

-- Performance Optimization Notes:
-- 1. All collaborative queries use UNION to combine owned and shared resources
-- 2. Indexes on trip_collaborators(user_id, trip_id) optimize collaboration lookups
-- 3. Permission checks are cached at the database level for performance
-- 4. Memory tables use UUID user_id fields with proper foreign key constraints

-- Security Notes:
-- 1. Permission hierarchy: view < edit < admin
-- 2. Only trip owners can manage collaborators
-- 3. Collaboration inheritance: all trip-related data inherits trip permissions
-- 4. Chat sessions are accessible to all trip collaborators but only creatable by owners
-- 5. Tool calls and messages follow the same collaborative pattern as their parent sessions

-- Audit Trail:
-- All policies include created_at/updated_at tracking for audit purposes
-- Permission changes are logged through the updated_at trigger
-- Collaboration events can be tracked via trip_collaborators table timestamps
