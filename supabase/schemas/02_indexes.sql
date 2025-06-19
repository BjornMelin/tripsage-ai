-- Performance Indexes Schema
-- Description: Comprehensive indexing strategy for optimal query performance
-- Dependencies: 01_tables.sql (all table definitions)
-- Based on: pgvector, Supabase, and PostgreSQL best practices research

-- ===========================
-- CORE TRIP MANAGEMENT INDEXES
-- ===========================

-- Primary foreign key indexes for RLS performance
CREATE INDEX IF NOT EXISTS idx_trips_user_id ON trips(user_id);
CREATE INDEX IF NOT EXISTS idx_trip_collaborators_trip_id ON trip_collaborators(trip_id);
CREATE INDEX IF NOT EXISTS idx_trip_collaborators_user_id ON trip_collaborators(user_id);
CREATE INDEX IF NOT EXISTS idx_trip_collaborators_added_by ON trip_collaborators(added_by);

-- Composite index for trip collaboration queries (highly optimized)
CREATE INDEX IF NOT EXISTS idx_trip_collaborators_user_trip ON trip_collaborators(user_id, trip_id);
CREATE INDEX IF NOT EXISTS idx_trip_collaborators_trip_permission ON trip_collaborators(trip_id, permission_level);

-- Trip search and filtering indexes
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
CREATE INDEX IF NOT EXISTS idx_trips_trip_type ON trips(trip_type);
CREATE INDEX IF NOT EXISTS idx_trips_start_date ON trips(start_date);
CREATE INDEX IF NOT EXISTS idx_trips_end_date ON trips(end_date);
CREATE INDEX IF NOT EXISTS idx_trips_destination ON trips(destination);

-- Trip date range queries (composite for better performance)
CREATE INDEX IF NOT EXISTS idx_trips_user_dates ON trips(user_id, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_trips_status_dates ON trips(status, start_date, end_date);

-- ===========================
-- TRAVEL OPTIONS INDEXES
-- ===========================

-- Flight indexes for collaborative access
CREATE INDEX IF NOT EXISTS idx_flights_trip_id ON flights(trip_id);
CREATE INDEX IF NOT EXISTS idx_flights_booking_status ON flights(booking_status);
CREATE INDEX IF NOT EXISTS idx_flights_origin ON flights(origin);
CREATE INDEX IF NOT EXISTS idx_flights_destination ON flights(destination);
CREATE INDEX IF NOT EXISTS idx_flights_departure_date ON flights(departure_date);
CREATE INDEX IF NOT EXISTS idx_flights_airline ON flights(airline);

-- Accommodation indexes
CREATE INDEX IF NOT EXISTS idx_accommodations_trip_id ON accommodations(trip_id);
CREATE INDEX IF NOT EXISTS idx_accommodations_booking_status ON accommodations(booking_status);
CREATE INDEX IF NOT EXISTS idx_accommodations_check_in_date ON accommodations(check_in_date);
CREATE INDEX IF NOT EXISTS idx_accommodations_check_out_date ON accommodations(check_out_date);
CREATE INDEX IF NOT EXISTS idx_accommodations_rating ON accommodations(rating);

-- Transportation indexes
CREATE INDEX IF NOT EXISTS idx_transportation_trip_id ON transportation(trip_id);
CREATE INDEX IF NOT EXISTS idx_transportation_transport_type ON transportation(transport_type);
CREATE INDEX IF NOT EXISTS idx_transportation_booking_status ON transportation(booking_status);
CREATE INDEX IF NOT EXISTS idx_transportation_departure_time ON transportation(departure_time);

-- Itinerary items indexes
CREATE INDEX IF NOT EXISTS idx_itinerary_items_trip_id ON itinerary_items(trip_id);
CREATE INDEX IF NOT EXISTS idx_itinerary_items_item_type ON itinerary_items(item_type);
CREATE INDEX IF NOT EXISTS idx_itinerary_items_booking_status ON itinerary_items(booking_status);
CREATE INDEX IF NOT EXISTS idx_itinerary_items_start_time ON itinerary_items(start_time);

-- ===========================
-- CHAT SYSTEM INDEXES
-- ===========================

-- Chat session indexes for RLS and collaboration
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_trip_id ON chat_sessions(trip_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at DESC);

-- Composite index for collaborative chat access
CREATE INDEX IF NOT EXISTS idx_chat_sessions_trip_user ON chat_sessions(trip_id, user_id);

-- Chat message indexes for performance
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_role ON chat_messages(role);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at DESC);

-- Composite index for message retrieval (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(session_id, created_at DESC);

-- Chat tool calls indexes
CREATE INDEX IF NOT EXISTS idx_chat_tool_calls_message_id ON chat_tool_calls(message_id);
CREATE INDEX IF NOT EXISTS idx_chat_tool_calls_status ON chat_tool_calls(status);
CREATE INDEX IF NOT EXISTS idx_chat_tool_calls_tool_name ON chat_tool_calls(tool_name);
CREATE INDEX IF NOT EXISTS idx_chat_tool_calls_created_at ON chat_tool_calls(created_at DESC);

-- ===========================
-- API KEYS INDEXES
-- ===========================

-- API key indexes for BYOK performance
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_service_name ON api_keys(service_name);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);

-- Composite index for key lookup (most common pattern)
CREATE INDEX IF NOT EXISTS idx_api_keys_user_service ON api_keys(user_id, service_name, is_active);

-- ===========================
-- MEMORY SYSTEM INDEXES (pgvector optimized)
-- ===========================

-- Memory table user indexes for RLS performance
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_memory_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);

-- Vector index for semantic search (IVFFlat with cosine distance)
-- Using 100 lists as recommended for initial deployment, can be tuned based on data size
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Session memory indexes
CREATE INDEX IF NOT EXISTS idx_session_memories_user_id ON session_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_session_memories_session_id ON session_memories(session_id);
CREATE INDEX IF NOT EXISTS idx_session_memories_created_at ON session_memories(created_at DESC);

-- Vector index for session memory search
CREATE INDEX IF NOT EXISTS idx_session_memories_embedding ON session_memories 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- Composite index for memory retrieval patterns
CREATE INDEX IF NOT EXISTS idx_memories_user_type ON memories(user_id, memory_type);
CREATE INDEX IF NOT EXISTS idx_session_memories_session_user ON session_memories(session_id, user_id);

-- ===========================
-- PERFORMANCE MONITORING INDEXES
-- ===========================

-- Recent activity monitoring (using immutable expressions)
CREATE INDEX IF NOT EXISTS idx_chat_messages_recent_activity ON chat_messages(created_at DESC)
WHERE created_at > '2024-01-01'::timestamp with time zone;

-- Active collaboration monitoring
CREATE INDEX IF NOT EXISTS idx_trip_collaborators_active ON trip_collaborators(added_at DESC, permission_level)
WHERE permission_level IN ('edit', 'admin');

-- Memory cleanup index for maintenance functions
CREATE INDEX IF NOT EXISTS idx_memories_cleanup ON memories(created_at, user_id)
WHERE created_at < NOW() - INTERVAL '30 days';

-- Session cleanup index
CREATE INDEX IF NOT EXISTS idx_session_memories_cleanup ON session_memories(created_at)
WHERE created_at < NOW() - INTERVAL '7 days';

-- ===========================
-- COMPOSITE COLLABORATION INDEXES
-- ===========================

-- Optimized index for get_user_accessible_trips function
CREATE INDEX IF NOT EXISTS idx_trips_collaboration_access ON trips(user_id, status, created_at DESC);

-- Index for permission hierarchy queries
CREATE INDEX IF NOT EXISTS idx_trip_collaborators_permission_hierarchy ON trip_collaborators(
    trip_id, 
    permission_level, 
    user_id
) WHERE permission_level IN ('view', 'edit', 'admin');

-- Chat access pattern for collaborative trips
CREATE INDEX IF NOT EXISTS idx_chat_collaborative_access ON chat_sessions(trip_id, created_at DESC)
WHERE trip_id IS NOT NULL;

-- ===========================
-- SEARCH AND FILTERING INDEXES
-- ===========================

-- Trip search patterns
CREATE INDEX IF NOT EXISTS idx_trips_search_pattern ON trips(destination, status, start_date);
CREATE INDEX IF NOT EXISTS idx_trips_budget_range ON trips(budget, travelers, trip_type);

-- Flight search patterns
CREATE INDEX IF NOT EXISTS idx_flights_search_pattern ON flights(origin, destination, departure_date, flight_class);
CREATE INDEX IF NOT EXISTS idx_flights_price_range ON flights(price, currency, booking_status);

-- Accommodation search patterns
CREATE INDEX IF NOT EXISTS idx_accommodations_search_pattern ON accommodations(
    check_in_date, 
    check_out_date, 
    rating, 
    booking_status
);

-- ===========================
-- MAINTENANCE AND CLEANUP INDEXES
-- ===========================

-- Expired session cleanup
CREATE INDEX IF NOT EXISTS idx_chat_sessions_expired ON chat_sessions(ended_at)
WHERE ended_at IS NULL;

-- API key expiration monitoring
CREATE INDEX IF NOT EXISTS idx_api_keys_expiration ON api_keys(expires_at, is_active)
WHERE expires_at IS NOT NULL;

-- ===========================
-- GIN INDEXES FOR JSONB COLUMNS
-- ===========================

-- Metadata search indexes using GIN
CREATE INDEX IF NOT EXISTS idx_trips_search_metadata_gin ON trips USING gin(search_metadata);
CREATE INDEX IF NOT EXISTS idx_flights_metadata_gin ON flights USING gin(metadata);
CREATE INDEX IF NOT EXISTS idx_accommodations_metadata_gin ON accommodations USING gin(metadata);
CREATE INDEX IF NOT EXISTS idx_memories_metadata_gin ON memories USING gin(metadata);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_metadata_gin ON chat_sessions USING gin(metadata);

-- ===========================
-- PARTIAL INDEXES FOR OPTIMIZATION
-- ===========================

-- Active items only indexes (avoid indexing completed/cancelled items)
CREATE INDEX IF NOT EXISTS idx_trips_active_only ON trips(user_id, start_date)
WHERE status IN ('planning', 'booked');

CREATE INDEX IF NOT EXISTS idx_flights_available_only ON flights(trip_id, departure_date)
WHERE booking_status = 'available';

CREATE INDEX IF NOT EXISTS idx_accommodations_available_only ON accommodations(trip_id, check_in_date)
WHERE booking_status = 'available';

-- Recent messages only (performance optimization)
CREATE INDEX IF NOT EXISTS idx_chat_messages_recent_only ON chat_messages(session_id, created_at DESC)
WHERE created_at > NOW() - INTERVAL '30 days';

-- ===========================
-- INDEX COMMENTS (Documentation)
-- ===========================

COMMENT ON INDEX idx_memories_embedding IS 'IVFFlat vector index for semantic memory search using cosine distance. Optimized for 1536-dimension embeddings (OpenAI compatible).';

COMMENT ON INDEX idx_trip_collaborators_user_trip IS 'Composite index optimizing RLS policies for collaborative trip access. Critical for performance.';

COMMENT ON INDEX idx_chat_messages_session_created IS 'Optimized for get_recent_messages() function - most common chat query pattern.';

COMMENT ON INDEX idx_trips_collaboration_access IS 'Optimized for get_user_accessible_trips() function in collaboration workflows.';

COMMENT ON INDEX idx_session_memories_embedding IS 'Vector index for session-specific memory search. Smaller lists parameter due to shorter-lived data.';

-- ===========================
-- FILE ATTACHMENTS INDEXES
-- ===========================

-- Primary access patterns for file attachments
CREATE INDEX IF NOT EXISTS idx_file_attachments_user_id ON file_attachments(user_id);
CREATE INDEX IF NOT EXISTS idx_file_attachments_trip_id ON file_attachments(trip_id);
CREATE INDEX IF NOT EXISTS idx_file_attachments_chat_message_id ON file_attachments(chat_message_id);
CREATE INDEX IF NOT EXISTS idx_file_attachments_upload_status ON file_attachments(upload_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_file_attachments_virus_scan ON file_attachments(virus_scan_status, created_at DESC);

-- Compound index for user file management
CREATE INDEX IF NOT EXISTS idx_file_attachments_user_trip ON file_attachments(user_id, trip_id, created_at DESC);

-- Index for file cleanup operations
CREATE INDEX IF NOT EXISTS idx_file_attachments_cleanup ON file_attachments(upload_status, created_at)
WHERE upload_status IN ('failed') OR created_at < NOW() - INTERVAL '7 days';

-- ===========================
-- SEARCH CACHE INDEXES
-- ===========================

-- Search destinations indexes
CREATE INDEX IF NOT EXISTS idx_search_destinations_user_id ON search_destinations(user_id);
CREATE INDEX IF NOT EXISTS idx_search_destinations_hash ON search_destinations(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_destinations_expires ON search_destinations(expires_at);
CREATE INDEX IF NOT EXISTS idx_search_destinations_cleanup ON search_destinations(expires_at) 
WHERE expires_at < NOW();

-- Search activities indexes
CREATE INDEX IF NOT EXISTS idx_search_activities_user_id ON search_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_search_activities_destination ON search_activities(destination, activity_type);
CREATE INDEX IF NOT EXISTS idx_search_activities_hash ON search_activities(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_activities_expires ON search_activities(expires_at);
CREATE INDEX IF NOT EXISTS idx_search_activities_cleanup ON search_activities(expires_at) 
WHERE expires_at < NOW();

-- Search flights indexes
CREATE INDEX IF NOT EXISTS idx_search_flights_user_id ON search_flights(user_id);
CREATE INDEX IF NOT EXISTS idx_search_flights_route ON search_flights(origin, destination, departure_date);
CREATE INDEX IF NOT EXISTS idx_search_flights_hash ON search_flights(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_flights_expires ON search_flights(expires_at);
CREATE INDEX IF NOT EXISTS idx_search_flights_cleanup ON search_flights(expires_at) 
WHERE expires_at < NOW();

-- Search hotels indexes
CREATE INDEX IF NOT EXISTS idx_search_hotels_user_id ON search_hotels(user_id);
CREATE INDEX IF NOT EXISTS idx_search_hotels_destination_dates ON search_hotels(destination, check_in_date, check_out_date);
CREATE INDEX IF NOT EXISTS idx_search_hotels_hash ON search_hotels(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_hotels_expires ON search_hotels(expires_at);
CREATE INDEX IF NOT EXISTS idx_search_hotels_cleanup ON search_hotels(expires_at) 
WHERE expires_at < NOW();

-- ===========================
-- SEARCH CACHE PERFORMANCE INDEXES
-- ===========================

-- Compound indexes for search optimization
CREATE INDEX IF NOT EXISTS idx_search_destinations_user_query ON search_destinations(user_id, query_hash, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_activities_user_dest_type ON search_activities(user_id, destination, activity_type, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_flights_user_route_class ON search_flights(user_id, origin, destination, cabin_class, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_hotels_user_dest_guests ON search_hotels(user_id, destination, guests, rooms, expires_at DESC);

-- ===========================
-- NEW INDEX COMMENTS
-- ===========================

COMMENT ON INDEX idx_file_attachments_user_trip IS 'Optimized for user file browsing within specific trips. Critical for file management UI.';

COMMENT ON INDEX idx_search_destinations_user_query IS 'Optimized for cache hit lookups by user and query hash. Prevents duplicate API calls.';

COMMENT ON INDEX idx_search_flights_user_route_class IS 'Optimized for flight search cache lookups. Includes all common filter parameters.';

COMMENT ON INDEX idx_search_hotels_user_dest_guests IS 'Optimized for hotel search cache lookups. Accounts for guest and room requirements.';