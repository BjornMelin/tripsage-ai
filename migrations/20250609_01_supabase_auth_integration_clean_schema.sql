-- Migration: Supabase Auth Integration - Clean Schema
-- Description: Creates clean schema that properly integrates with Supabase Auth
-- Created: 2025-06-09
-- Replaces: All previous migrations - this creates the final, correct schema

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Note: Supabase automatically creates auth.users table with UUID primary keys
-- We reference auth.users(id) for all user relationships

-- ===========================
-- CORE TRIP MANAGEMENT TABLES  
-- ===========================

-- Create trips table (FIXED: now includes user_id relationship)
CREATE TABLE IF NOT EXISTS trips (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    destination TEXT NOT NULL,
    budget NUMERIC NOT NULL,
    travelers INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'planning',
    trip_type TEXT NOT NULL DEFAULT 'leisure',
    flexibility JSONB DEFAULT '{}',
    notes TEXT[],
    search_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT trips_date_check CHECK (end_date >= start_date),
    CONSTRAINT trips_travelers_check CHECK (travelers > 0),
    CONSTRAINT trips_budget_check CHECK (budget > 0),
    CONSTRAINT trips_status_check CHECK (status IN ('planning', 'booked', 'completed', 'cancelled')),
    CONSTRAINT trips_type_check CHECK (trip_type IN ('leisure', 'business', 'family', 'solo', 'other'))
);

-- Create indexes for trips
CREATE INDEX idx_trips_user_id ON trips(user_id);
CREATE INDEX idx_trips_status ON trips(status);
CREATE INDEX idx_trips_dates ON trips(start_date, end_date);
CREATE INDEX idx_trips_created_at ON trips(created_at DESC);

COMMENT ON TABLE trips IS 'Travel trips planned by users - core entity with proper user ownership';
COMMENT ON COLUMN trips.user_id IS 'Reference to auth.users(id) - owner of this trip';
COMMENT ON COLUMN trips.notes IS 'Array of trip notes (replaces separate trip_notes table)';
COMMENT ON COLUMN trips.search_metadata IS 'Search parameters and filters (replaces separate search_parameters table)';

-- ===========================
-- TRAVEL OPTIONS TABLES
-- ===========================

-- Create flights table  
CREATE TABLE IF NOT EXISTS flights (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date DATE NOT NULL,
    return_date DATE,
    flight_class TEXT NOT NULL DEFAULT 'economy',
    price NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    airline TEXT,
    flight_number TEXT,
    booking_status TEXT NOT NULL DEFAULT 'available',
    external_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT flights_price_check CHECK (price >= 0),
    CONSTRAINT flights_class_check CHECK (flight_class IN ('economy', 'premium_economy', 'business', 'first')),
    CONSTRAINT flights_status_check CHECK (booking_status IN ('available', 'reserved', 'booked', 'cancelled'))
);

CREATE INDEX idx_flights_trip_id ON flights(trip_id);
CREATE INDEX idx_flights_dates ON flights(departure_date, return_date);
CREATE INDEX idx_flights_origin_dest ON flights(origin, destination);

-- Create accommodations table
CREATE TABLE IF NOT EXISTS accommodations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    address TEXT,
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    room_type TEXT,
    price_per_night NUMERIC NOT NULL,
    total_price NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    rating NUMERIC,
    amenities TEXT[],
    booking_status TEXT NOT NULL DEFAULT 'available',
    external_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT accommodations_price_check CHECK (price_per_night >= 0 AND total_price >= 0),
    CONSTRAINT accommodations_dates_check CHECK (check_out_date > check_in_date),
    CONSTRAINT accommodations_rating_check CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)),
    CONSTRAINT accommodations_status_check CHECK (booking_status IN ('available', 'reserved', 'booked', 'cancelled'))
);

CREATE INDEX idx_accommodations_trip_id ON accommodations(trip_id);
CREATE INDEX idx_accommodations_dates ON accommodations(check_in_date, check_out_date);
CREATE INDEX idx_accommodations_rating ON accommodations(rating DESC) WHERE rating IS NOT NULL;

-- Create transportation table (simplified)
CREATE TABLE IF NOT EXISTS transportation (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    transport_type TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_time TIMESTAMP WITH TIME ZONE,
    arrival_time TIMESTAMP WITH TIME ZONE,
    price NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    booking_status TEXT NOT NULL DEFAULT 'available',
    external_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT transportation_price_check CHECK (price >= 0),
    CONSTRAINT transportation_type_check CHECK (transport_type IN ('flight', 'train', 'bus', 'car_rental', 'taxi', 'other')),
    CONSTRAINT transportation_status_check CHECK (booking_status IN ('available', 'reserved', 'booked', 'cancelled'))
);

CREATE INDEX idx_transportation_trip_id ON transportation(trip_id);
CREATE INDEX idx_transportation_type ON transportation(transport_type);

-- Create itinerary_items table
CREATE TABLE IF NOT EXISTS itinerary_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    item_type TEXT NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    location TEXT,
    price NUMERIC DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    booking_status TEXT NOT NULL DEFAULT 'planned',
    external_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT itinerary_price_check CHECK (price >= 0),
    CONSTRAINT itinerary_type_check CHECK (item_type IN ('activity', 'meal', 'transport', 'accommodation', 'event', 'other')),
    CONSTRAINT itinerary_status_check CHECK (booking_status IN ('planned', 'reserved', 'booked', 'completed', 'cancelled'))
);

CREATE INDEX idx_itinerary_items_trip_id ON itinerary_items(trip_id);
CREATE INDEX idx_itinerary_items_start_time ON itinerary_items(start_time);
CREATE INDEX idx_itinerary_items_type ON itinerary_items(item_type);

-- ===========================
-- CHAT SYSTEM TABLES
-- ===========================

-- Create chat_sessions table (FIXED: user_id is now UUID)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    trip_id BIGINT REFERENCES trips(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_trip_id ON chat_sessions(trip_id);
CREATE INDEX idx_chat_sessions_created_at ON chat_sessions(created_at DESC);

-- Create chat_messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT chat_messages_role_check CHECK (role IN ('user', 'assistant', 'system')),
    CONSTRAINT chat_messages_content_length CHECK (length(content) <= 32768)
);

CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(session_id, created_at DESC);

-- Create chat_tool_calls table
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
    
    CONSTRAINT chat_tool_calls_status_check CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE INDEX idx_chat_tool_calls_message_id ON chat_tool_calls(message_id);
CREATE INDEX idx_chat_tool_calls_tool_name ON chat_tool_calls(tool_name);

-- ===========================
-- API KEYS TABLE (BYOK)
-- ===========================

-- Create api_keys table (FIXED: user_id is now UUID)
CREATE TABLE IF NOT EXISTS api_keys (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    service_name TEXT NOT NULL,
    key_name TEXT NOT NULL,
    encrypted_key TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT api_keys_user_service_key_unique UNIQUE (user_id, service_name, key_name)
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_service ON api_keys(service_name);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);

-- ===========================
-- MEMORY SYSTEM TABLES (Mem0 + pgvector)
-- ===========================

-- Create memories table (already UUID compatible)
CREATE TABLE IF NOT EXISTS memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL, -- Using TEXT to store UUID from auth.users
    memory_type TEXT NOT NULL DEFAULT 'user_preference',
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT memories_type_check CHECK (memory_type IN ('user_preference', 'trip_history', 'search_pattern', 'conversation_context', 'other'))
);

CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_type ON memories(memory_type);
CREATE INDEX idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create session_memories table (temporary conversation context)
CREATE TABLE IF NOT EXISTS session_memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL, -- Using TEXT to store UUID from auth.users
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT session_memories_content_length CHECK (length(content) <= 8192)
);

CREATE INDEX idx_session_memories_session_id ON session_memories(session_id);
CREATE INDEX idx_session_memories_user_id ON session_memories(user_id);
CREATE INDEX idx_session_memories_embedding ON session_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

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

-- Create triggers for updated_at columns
CREATE TRIGGER update_trips_updated_at BEFORE UPDATE ON trips FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_flights_updated_at BEFORE UPDATE ON flights FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_accommodations_updated_at BEFORE UPDATE ON accommodations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_chat_sessions_updated_at BEFORE UPDATE ON chat_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===========================
-- ROW LEVEL SECURITY (RLS)
-- ===========================

-- Enable RLS on all user-owned tables
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for trips
CREATE POLICY "Users can only access their own trips" ON trips
    FOR ALL USING (auth.uid() = user_id);

-- Create RLS policies for chat_sessions
CREATE POLICY "Users can only access their own chat sessions" ON chat_sessions
    FOR ALL USING (auth.uid() = user_id);

-- Create RLS policies for api_keys
CREATE POLICY "Users can only access their own API keys" ON api_keys
    FOR ALL USING (auth.uid() = user_id);

-- Create policies for related tables (they inherit user access through foreign keys)
ALTER TABLE flights ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can access flights for their trips" ON flights
    FOR ALL USING (trip_id IN (SELECT id FROM trips WHERE user_id = auth.uid()));

ALTER TABLE accommodations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can access accommodations for their trips" ON accommodations
    FOR ALL USING (trip_id IN (SELECT id FROM trips WHERE user_id = auth.uid()));

ALTER TABLE transportation ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can access transportation for their trips" ON transportation
    FOR ALL USING (trip_id IN (SELECT id FROM trips WHERE user_id = auth.uid()));

ALTER TABLE itinerary_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can access itinerary items for their trips" ON itinerary_items
    FOR ALL USING (trip_id IN (SELECT id FROM trips WHERE user_id = auth.uid()));

ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can access messages in their chat sessions" ON chat_messages
    FOR ALL USING (session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid()));

ALTER TABLE chat_tool_calls ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can access tool calls in their messages" ON chat_tool_calls
    FOR ALL USING (message_id IN (
        SELECT cm.id FROM chat_messages cm 
        JOIN chat_sessions cs ON cm.session_id = cs.id 
        WHERE cs.user_id = auth.uid()
    ));

-- ===========================
-- HELPFUL VIEWS
-- ===========================

-- Create view for active chat sessions with statistics
CREATE OR REPLACE VIEW active_chat_sessions AS
SELECT 
    cs.id,
    cs.user_id,
    cs.trip_id,
    cs.created_at,
    cs.updated_at,
    cs.metadata,
    COUNT(cm.id) as message_count,
    MAX(cm.created_at) as last_message_at
FROM chat_sessions cs
LEFT JOIN chat_messages cm ON cs.id = cm.session_id
WHERE cs.ended_at IS NULL
GROUP BY cs.id, cs.user_id, cs.trip_id, cs.created_at, cs.updated_at, cs.metadata;

-- Create view for trip summaries
CREATE OR REPLACE VIEW trip_summaries AS
SELECT 
    t.id,
    t.user_id,
    t.name,
    t.destination,
    t.start_date,
    t.end_date,
    t.budget,
    t.status,
    COUNT(DISTINCT f.id) as flight_count,
    COUNT(DISTINCT a.id) as accommodation_count,
    COUNT(DISTINCT ii.id) as itinerary_item_count,
    SUM(f.price) as total_flight_cost,
    SUM(a.total_price) as total_accommodation_cost
FROM trips t
LEFT JOIN flights f ON t.id = f.trip_id
LEFT JOIN accommodations a ON t.id = a.trip_id  
LEFT JOIN itinerary_items ii ON t.id = ii.trip_id
GROUP BY t.id, t.user_id, t.name, t.destination, t.start_date, t.end_date, t.budget, t.status;

-- ===========================
-- COMMENTS
-- ===========================

COMMENT ON TABLE trips IS 'Travel trips - now properly linked to auth.users with UUID references';
COMMENT ON TABLE chat_sessions IS 'Chat sessions - now properly linked to auth.users with UUID references';
COMMENT ON TABLE api_keys IS 'User API keys for BYOK - now properly linked to auth.users with UUID references';
COMMENT ON TABLE memories IS 'Memory system for personalization - compatible with Supabase Auth';
COMMENT ON TABLE session_memories IS 'Temporary conversation context - compatible with Supabase Auth';

-- This migration creates a clean, production-ready schema that:
-- 1. Properly integrates with Supabase Auth (uses auth.users)
-- 2. Includes Row Level Security for multi-tenant isolation
-- 3. Fixes the missing user-trip relationship
-- 4. Removes unnecessary complexity
-- 5. Supports all current functionality (chat, trips, API keys, memory)