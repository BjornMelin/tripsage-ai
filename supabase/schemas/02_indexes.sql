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