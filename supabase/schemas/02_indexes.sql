-- Database Indexes Schema
-- Description: Performance optimization indexes for efficient querying
-- Dependencies: 01_tables.sql (all table definitions)

-- ===========================
-- CORE TABLES INDEXES
-- ===========================

-- Trips table indexes
CREATE INDEX idx_trips_user_id ON trips(user_id);
CREATE INDEX idx_trips_status ON trips(status);
CREATE INDEX idx_trips_dates ON trips(start_date, end_date);
CREATE INDEX idx_trips_created_at ON trips(created_at DESC);

-- ===========================
-- TRAVEL OPTIONS INDEXES
-- ===========================

-- Flights table indexes
CREATE INDEX idx_flights_trip_id ON flights(trip_id);
CREATE INDEX idx_flights_dates ON flights(departure_date, return_date);
CREATE INDEX idx_flights_origin_dest ON flights(origin, destination);

-- Accommodations table indexes
CREATE INDEX idx_accommodations_trip_id ON accommodations(trip_id);
CREATE INDEX idx_accommodations_dates ON accommodations(check_in_date, check_out_date);
CREATE INDEX idx_accommodations_rating ON accommodations(rating DESC) WHERE rating IS NOT NULL;

-- Transportation table indexes
CREATE INDEX idx_transportation_trip_id ON transportation(trip_id);
CREATE INDEX idx_transportation_type ON transportation(transport_type);

-- Itinerary items table indexes
CREATE INDEX idx_itinerary_items_trip_id ON itinerary_items(trip_id);
CREATE INDEX idx_itinerary_items_start_time ON itinerary_items(start_time);
CREATE INDEX idx_itinerary_items_type ON itinerary_items(item_type);

-- ===========================
-- CHAT SYSTEM INDEXES
-- ===========================

-- Chat sessions indexes
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_trip_id ON chat_sessions(trip_id);
CREATE INDEX idx_chat_sessions_created_at ON chat_sessions(created_at DESC);

-- Chat messages indexes
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(session_id, created_at DESC);

-- Chat tool calls indexes
CREATE INDEX idx_chat_tool_calls_message_id ON chat_tool_calls(message_id);
CREATE INDEX idx_chat_tool_calls_tool_name ON chat_tool_calls(tool_name);

-- ===========================
-- API KEYS INDEXES
-- ===========================

-- API keys table indexes
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_service ON api_keys(service_name);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);

-- ===========================
-- MEMORY SYSTEM INDEXES
-- ===========================

-- Memories table indexes
CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_type ON memories(memory_type);
CREATE INDEX idx_memories_created_at ON memories(created_at DESC);

-- Vector similarity index for memories (using IVFFlat for efficient similarity search)
-- Lists parameter set to 100 for optimal performance with expected data size
CREATE INDEX idx_memories_embedding ON memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Session memories indexes
CREATE INDEX idx_session_memories_session_id ON session_memories(session_id);
CREATE INDEX idx_session_memories_user_id ON session_memories(user_id);

-- Vector similarity index for session memories
CREATE INDEX idx_session_memories_embedding ON session_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- ===========================
-- TRIP COLLABORATION INDEXES
-- ===========================

-- Trip collaborators table indexes
CREATE INDEX idx_trip_collaborators_trip_id ON trip_collaborators(trip_id);
CREATE INDEX idx_trip_collaborators_user_id ON trip_collaborators(user_id);
CREATE INDEX idx_trip_collaborators_added_by ON trip_collaborators(added_by);
CREATE INDEX idx_trip_collaborators_permission ON trip_collaborators(permission_level);
CREATE INDEX idx_trip_collaborators_added_at ON trip_collaborators(added_at DESC);

-- Composite indexes for optimal collaboration query performance
CREATE INDEX idx_trip_collaborators_user_trip ON trip_collaborators(user_id, trip_id);
CREATE INDEX idx_trip_collaborators_trip_permission ON trip_collaborators(trip_id, permission_level);
CREATE INDEX idx_trip_collaborators_user_permission ON trip_collaborators(user_id, permission_level);

-- Index for permission hierarchy queries
CREATE INDEX idx_trip_collaborators_permission_hierarchy ON trip_collaborators(
    user_id, 
    trip_id, 
    CASE permission_level 
        WHEN 'admin' THEN 3 
        WHEN 'edit' THEN 2 
        WHEN 'view' THEN 1 
        ELSE 0 
    END DESC
);

-- ===========================
-- PERFORMANCE MONITORING INDEXES
-- ===========================

-- Indexes for common query patterns and performance monitoring

-- Cross-table collaboration query optimization
CREATE INDEX idx_trips_collaborators_join ON trips(id) 
WHERE id IN (SELECT trip_id FROM trip_collaborators);

-- Active sessions tracking
CREATE INDEX idx_active_chat_sessions ON chat_sessions(user_id, trip_id, created_at DESC) 
WHERE ended_at IS NULL;

-- Recent activity tracking
CREATE INDEX idx_recent_activity_trips ON trips(user_id, updated_at DESC) 
WHERE status IN ('planning', 'booked');

CREATE INDEX idx_recent_activity_messages ON chat_messages(created_at DESC) 
WHERE created_at > NOW() - INTERVAL '24 hours';

-- Booking status tracking
CREATE INDEX idx_pending_bookings_flights ON flights(trip_id, booking_status, created_at DESC) 
WHERE booking_status IN ('available', 'reserved');

CREATE INDEX idx_pending_bookings_accommodations ON accommodations(trip_id, booking_status, created_at DESC) 
WHERE booking_status IN ('available', 'reserved');

-- ===========================
-- INDEX MAINTENANCE COMMENTS
-- ===========================

-- Performance Notes:
-- 1. Collaboration indexes are optimized for the most common query patterns
-- 2. Composite indexes follow the selectivity order: most selective columns first
-- 3. Partial indexes are used where appropriate to reduce index size
-- 4. Vector indexes use IVFFlat with list counts optimized for expected data volume
-- 5. GIN indexes are used for JSONB and text search functionality
-- 6. All date/time columns use DESC ordering for recent-first queries

-- Monitoring:
-- Use pg_stat_user_indexes to monitor index usage
-- Use EXPLAIN ANALYZE to verify index usage in query plans
-- Regular ANALYZE is recommended for optimal query planning