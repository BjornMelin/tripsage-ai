-- Core Tables Schema
-- Description: Primary business logic tables for TripSage travel planning system
-- Dependencies: 00_extensions.sql (uuid-ossp, vector extensions)

-- ===========================
-- CORE TRIP MANAGEMENT TABLES  
-- ===========================

-- Create trips table (core entity with proper user ownership)
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

-- ===========================
-- CHAT SYSTEM TABLES
-- ===========================

-- Create chat_sessions table (with proper UUID user references)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    trip_id BIGINT REFERENCES trips(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

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

-- ===========================
-- API KEYS TABLE (BYOK)
-- ===========================

-- Create api_keys table (BYOK - Bring Your Own Keys)
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

-- ===========================
-- MEMORY SYSTEM TABLES (Mem0 + pgvector)
-- ===========================

-- Create memories table (for long-term user preferences and history)
CREATE TABLE IF NOT EXISTS memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL DEFAULT 'user_preference',
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT memories_type_check CHECK (memory_type IN ('user_preference', 'trip_history', 'search_pattern', 'conversation_context', 'other'))
);

-- Create session_memories table (temporary conversation context)
CREATE TABLE IF NOT EXISTS session_memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT session_memories_content_length CHECK (length(content) <= 8192)
);

-- ===========================
-- TRIP COLLABORATION TABLES
-- ===========================

-- Create trip_collaborators table (for sharing trips with other users)
CREATE TABLE IF NOT EXISTS trip_collaborators (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    permission_level TEXT NOT NULL DEFAULT 'view',
    added_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT trip_collaborators_permission_check CHECK (permission_level IN ('view', 'edit', 'admin')),
    CONSTRAINT trip_collaborators_unique UNIQUE (trip_id, user_id)
);

-- ===========================
-- FILE STORAGE TABLES
-- ===========================

-- Create file_attachments table (for Supabase Storage integration)
CREATE TABLE IF NOT EXISTS file_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    trip_id BIGINT REFERENCES trips(id) ON DELETE CASCADE,
    chat_message_id BIGINT REFERENCES chat_messages(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    bucket_name TEXT NOT NULL DEFAULT 'attachments',
    upload_status TEXT NOT NULL DEFAULT 'uploading',
    virus_scan_status TEXT DEFAULT 'pending',
    virus_scan_result JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT file_attachments_size_check CHECK (file_size > 0),
    CONSTRAINT file_attachments_upload_status_check CHECK (upload_status IN ('uploading', 'completed', 'failed')),
    CONSTRAINT file_attachments_virus_status_check CHECK (virus_scan_status IN ('pending', 'clean', 'infected', 'failed'))
);

-- ===========================
-- SEARCH CACHE TABLES
-- ===========================

-- Create search_destinations table (for destination search caching)
CREATE TABLE IF NOT EXISTS search_destinations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    results JSONB NOT NULL,
    source TEXT NOT NULL,
    search_metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT search_destinations_source_check CHECK (source IN ('google_maps', 'external_api', 'cached'))
);

-- Create search_activities table (for activity search caching)
CREATE TABLE IF NOT EXISTS search_activities (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    destination TEXT NOT NULL,
    activity_type TEXT,
    query_parameters JSONB NOT NULL,
    query_hash TEXT NOT NULL,
    results JSONB NOT NULL,
    source TEXT NOT NULL,
    search_metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT search_activities_source_check CHECK (source IN ('viator', 'getyourguide', 'external_api', 'cached'))
);

-- Create search_flights table (for flight search caching)
CREATE TABLE IF NOT EXISTS search_flights (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date DATE NOT NULL,
    return_date DATE,
    passengers INTEGER NOT NULL DEFAULT 1,
    cabin_class TEXT NOT NULL DEFAULT 'economy',
    query_parameters JSONB NOT NULL,
    query_hash TEXT NOT NULL,
    results JSONB NOT NULL,
    source TEXT NOT NULL,
    search_metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT search_flights_passengers_check CHECK (passengers > 0),
    CONSTRAINT search_flights_cabin_check CHECK (cabin_class IN ('economy', 'premium_economy', 'business', 'first')),
    CONSTRAINT search_flights_source_check CHECK (source IN ('duffel', 'amadeus', 'external_api', 'cached'))
);

-- Create search_hotels table (for hotel search caching)
CREATE TABLE IF NOT EXISTS search_hotels (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    destination TEXT NOT NULL,
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    guests INTEGER NOT NULL DEFAULT 1,
    rooms INTEGER NOT NULL DEFAULT 1,
    query_parameters JSONB NOT NULL,
    query_hash TEXT NOT NULL,
    results JSONB NOT NULL,
    source TEXT NOT NULL,
    search_metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT search_hotels_guests_check CHECK (guests > 0),
    CONSTRAINT search_hotels_rooms_check CHECK (rooms > 0),
    CONSTRAINT search_hotels_dates_check CHECK (check_out_date > check_in_date),
    CONSTRAINT search_hotels_source_check CHECK (source IN ('booking', 'expedia', 'airbnb_mcp', 'external_api', 'cached'))
);