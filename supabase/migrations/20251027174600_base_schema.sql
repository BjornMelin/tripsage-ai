-- TripSage Base Schema (consolidated)
-- Generated: 2025-10-27
-- This migration consolidates the canonical database schema from supabase/schemas.
-- FINAL-ONLY: the supabase/schemas and supabase/storage folders are legacy and will be removed.

-- ===========================
-- 00_extensions.sql
-- ===========================

-- Supabase Extensions Setup
-- Description: Required extensions for TripSage database functionality
-- Dependencies: None (must be run first)
-- Version: 2.0 - Includes automation and real-time capabilities

-- ===========================
-- CORE EXTENSIONS
-- ===========================

-- Enable UUID extension for generating unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension for AI/ML embeddings and semantic search
-- Note: This extension provides vector data types and operations for storing
-- and querying high-dimensional vectors (embeddings) efficiently
CREATE EXTENSION IF NOT EXISTS "vector";

-- ===========================
-- AUTOMATION EXTENSIONS
-- ===========================

-- Enable pg_cron for scheduled job automation
-- Documentation: https://github.com/citusdata/pg_cron
-- Used for: Automated maintenance, data cleanup, cache expiration
CREATE EXTENSION IF NOT EXISTS "pg_cron";

-- Grant usage on pg_cron schema to postgres user
GRANT USAGE ON SCHEMA cron TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cron TO postgres;

-- Enable pg_net for HTTP requests from database
-- Documentation: https://github.com/supabase/pg_net
-- Used for: Webhook notifications, external API calls, Edge Function triggers
CREATE EXTENSION IF NOT EXISTS "pg_net";

-- ===========================
-- PERFORMANCE EXTENSIONS
-- ===========================

-- Enable pg_stat_statements for query performance monitoring
-- Used for: Identifying slow queries and optimization opportunities
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Enable btree_gist for advanced indexing capabilities
-- Used for: Optimizing complex queries with multiple conditions
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- ===========================
-- SECURITY EXTENSIONS
-- ===========================

-- Enable pgcrypto for encryption functions
-- Used for: API key encryption, sensitive data protection
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ===========================
-- EXTENSION CONFIGURATION
-- ===========================

-- Configure pg_cron settings
-- NOTE: Managed Supabase prohibits ALTER SYSTEM. Skipping pg_cron database_name configuration.
-- ALTER SYSTEM SET cron.database_name = 'postgres';

-- Configure pg_net settings for optimal performance
-- Managed Supabase: skip ALTER SYSTEM for pg_net.
-- ALTER SYSTEM SET pg_net.batch_size = 200;
-- ALTER SYSTEM SET pg_net.ttl = '1 hour';

-- Configure pg_stat_statements
-- Managed Supabase: skip ALTER SYSTEM pg_stat_statements tuning.
-- ALTER SYSTEM SET pg_stat_statements.track = 'all';
-- ALTER SYSTEM SET pg_stat_statements.max = 10000;

-- Apply configuration changes
-- Managed Supabase: no reload needed for skipped ALTER SYSTEM.
-- SELECT pg_reload_conf();

-- ===========================
-- REALTIME CONFIGURATION
-- ===========================

-- Create publication for real-time updates
-- This enables Supabase Realtime for specific tables
DROP PUBLICATION IF EXISTS supabase_realtime CASCADE;
CREATE PUBLICATION supabase_realtime;

-- Add tables to real-time publication
-- Only include tables that require real-time updates for performance
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'trips') THEN
    EXECUTE 'ALTER PUBLICATION supabase_realtime ADD TABLE public.trips';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'chat_messages') THEN
    EXECUTE 'ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_messages';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'chat_sessions') THEN
    EXECUTE 'ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_sessions';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'trip_collaborators') THEN
    EXECUTE 'ALTER PUBLICATION supabase_realtime ADD TABLE public.trip_collaborators';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'itinerary_items') THEN
    EXECUTE 'ALTER PUBLICATION supabase_realtime ADD TABLE public.itinerary_items';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'chat_tool_calls') THEN
    EXECUTE 'ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_tool_calls';
  END IF;
END $$;

-- ===========================
-- EXTENSION VERIFICATION
-- ===========================

-- Create function to verify all extensions are properly installed
CREATE OR REPLACE FUNCTION verify_extensions()
RETURNS TABLE (
    extension_name TEXT,
    installed BOOLEAN,
    version TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ext.extname::TEXT,
        TRUE,
        ext.extversion::TEXT
    FROM pg_extension ext
    WHERE ext.extname IN (
        'uuid-ossp', 'vector', 'pg_cron', 'pg_net', 
        'pg_stat_statements', 'btree_gist', 'pgcrypto'
    )
    ORDER BY ext.extname;
END;
$$;

-- Note: Supabase automatically creates auth.users table with UUID primary keys
-- We reference auth.users(id) for all user relationships throughout the schema

-- Additional extensions to consider for future enhancements:
-- - pgvectorscale: High-performance vector indexing for improved embedding search performance
-- - pg_amqp: Message queue integration for advanced event processing
-- - pgtap: Testing framework for database functions and procedures
-- - plv8: JavaScript language for stored procedures (if needed)

-- ===========================
-- 01_tables.sql
-- ===========================

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
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- ===========================
-- 02_indexes.sql
-- ===========================

-- Performance Indexes Schema
-- Description: indexing strategy for optimal query performance
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

-- Composite index for key lookup (most common pattern)

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
-- Removed volatile partial index (NOW()) not allowed; rely on created_at index
CREATE INDEX IF NOT EXISTS idx_memories_created_at_user ON memories(created_at, user_id);

-- Session cleanup index
CREATE INDEX IF NOT EXISTS idx_session_memories_created_at ON session_memories(created_at);
-- Removed volatile partial index (NOW()) not allowed

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
-- Removed volatile partial index using NOW(); rely on existing session_id, created_at indexes

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
-- Removed volatile partial index; rely on upload_status and created_at indexes

-- ===========================
-- SEARCH CACHE INDEXES
-- ===========================

-- Search destinations indexes
CREATE INDEX IF NOT EXISTS idx_search_destinations_user_id ON search_destinations(user_id);
CREATE INDEX IF NOT EXISTS idx_search_destinations_hash ON search_destinations(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_destinations_expires ON search_destinations(expires_at);
-- Removed volatile partial index; rely on expires_at index

-- Search activities indexes
CREATE INDEX IF NOT EXISTS idx_search_activities_user_id ON search_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_search_activities_destination ON search_activities(destination, activity_type);
CREATE INDEX IF NOT EXISTS idx_search_activities_hash ON search_activities(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_activities_expires ON search_activities(expires_at);
-- Removed volatile partial index; rely on expires_at index

-- Search flights indexes
CREATE INDEX IF NOT EXISTS idx_search_flights_user_id ON search_flights(user_id);
CREATE INDEX IF NOT EXISTS idx_search_flights_route ON search_flights(origin, destination, departure_date);
CREATE INDEX IF NOT EXISTS idx_search_flights_hash ON search_flights(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_flights_expires ON search_flights(expires_at);
-- Removed volatile partial index; rely on expires_at index

-- Search hotels indexes
CREATE INDEX IF NOT EXISTS idx_search_hotels_user_id ON search_hotels(user_id);
CREATE INDEX IF NOT EXISTS idx_search_hotels_destination_dates ON search_hotels(destination, check_in_date, check_out_date);
CREATE INDEX IF NOT EXISTS idx_search_hotels_hash ON search_hotels(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_hotels_expires ON search_hotels(expires_at);
-- Removed volatile partial index; rely on expires_at index

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

-- ===========================
-- 03_functions.sql
-- ===========================

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
    query_user_id UUID,
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
    _rc INT := 0;
BEGIN
    -- Delete very old memories
    DELETE FROM memories 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_old;
    
    GET DIAGNOSTICS _rc = ROW_COUNT;
    deleted_count := deleted_count + _rc;
    
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
    
    GET DIAGNOSTICS _rc = ROW_COUNT;
    deleted_count := deleted_count + _rc;
    
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
  WITH base AS (
    SELECT
      id,
      role,
      content,
      created_at,
      metadata,
      LEAST(CEIL(LENGTH(content)::FLOAT / p_chars_per_token)::INTEGER, p_max_tokens) AS estimated_tokens
    FROM chat_messages
    WHERE session_id = p_session_id
    ORDER BY created_at DESC
    LIMIT p_limit OFFSET p_offset
  ), totals AS (
    SELECT COUNT(*)::BIGINT AS total_messages FROM chat_messages WHERE session_id = p_session_id
  )
  SELECT b.id, b.role, b.content, b.created_at, b.metadata, b.estimated_tokens, t.total_messages
  FROM base b CROSS JOIN totals t
  ORDER BY b.created_at
$$ LANGUAGE sql;

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
        '00000000-0000-0000-0000-000000000001'::UUID, 
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
    _rc INT := 0;
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
    
    GET DIAGNOSTICS _rc = ROW_COUNT;
    v_deleted_count := v_deleted_count + _rc;
    
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
    _rc INT := 0;
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
        
        GET DIAGNOSTICS _rc = ROW_COUNT;
        v_update_count := v_update_count + _rc;
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

-- ===========================
-- UTILITY SQL EXECUTION FUNCTIONS
-- ===========================

-- Function for safe SQL execution (with basic validation)
-- Note: This function is restricted and should only be used by service role
CREATE OR REPLACE FUNCTION execute_sql(
    p_sql_query TEXT,
    p_max_rows INT DEFAULT 1000
)
RETURNS TABLE (
    success BOOLEAN,
    result_count INT,
    execution_time_ms NUMERIC,
    error_message TEXT
) AS $$
DECLARE
    v_start_time TIMESTAMP;
    v_end_time TIMESTAMP;
    v_result_count INT := 0;
    v_error_message TEXT := NULL;
BEGIN
    -- Security: Only allow SELECT statements (prevent destructive operations)
    IF UPPER(TRIM(p_sql_query)) NOT LIKE 'SELECT%' THEN
        RETURN QUERY SELECT FALSE, 0, 0::NUMERIC, 'Only SELECT statements are allowed'::TEXT;
        RETURN;
    END IF;
    
    -- Security: Prevent potentially dangerous patterns
    IF p_sql_query ~* '(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)' THEN
        RETURN QUERY SELECT FALSE, 0, 0::NUMERIC, 'Query contains prohibited keywords'::TEXT;
        RETURN;
    END IF;
    
    v_start_time := clock_timestamp();
    
    BEGIN
        -- Execute the query with row limit
        EXECUTE format('SELECT COUNT(*) FROM (%s LIMIT %s) sub', p_sql_query, p_max_rows) INTO v_result_count;
        
        v_end_time := clock_timestamp();
        
        RETURN QUERY SELECT 
            TRUE,
            v_result_count,
            EXTRACT(MILLISECONDS FROM v_end_time - v_start_time),
            NULL::TEXT;
    EXCEPTION
        WHEN OTHERS THEN
            v_end_time := clock_timestamp();
            v_error_message := SQLERRM;
            
            RETURN QUERY SELECT 
                FALSE,
                0,
                EXTRACT(MILLISECONDS FROM v_end_time - v_start_time),
                v_error_message;
    END;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===========================
-- SEARCH CACHE CLEANUP FUNCTIONS
-- ===========================

-- Function to clean up expired search cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_search_cache()
RETURNS TABLE (
    table_name TEXT,
    deleted_count INT
) AS $$
DECLARE
    v_destinations_deleted INT;
    v_activities_deleted INT;
    v_flights_deleted INT;
    v_hotels_deleted INT;
BEGIN
    -- Clean up expired destination searches
    DELETE FROM search_destinations WHERE expires_at < NOW();
    GET DIAGNOSTICS v_destinations_deleted = ROW_COUNT;
    
    -- Clean up expired activity searches
    DELETE FROM search_activities WHERE expires_at < NOW();
    GET DIAGNOSTICS v_activities_deleted = ROW_COUNT;
    
    -- Clean up expired flight searches
    DELETE FROM search_flights WHERE expires_at < NOW();
    GET DIAGNOSTICS v_flights_deleted = ROW_COUNT;
    
    -- Clean up expired hotel searches
    DELETE FROM search_hotels WHERE expires_at < NOW();
    GET DIAGNOSTICS v_hotels_deleted = ROW_COUNT;
    
    -- Return cleanup results
    RETURN QUERY VALUES 
        ('search_destinations', v_destinations_deleted),
        ('search_activities', v_activities_deleted),
        ('search_flights', v_flights_deleted),
        ('search_hotels', v_hotels_deleted);
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- COLLABORATION EVENT TRIGGER FUNCTIONS
-- ===========================

-- Function to notify on collaboration changes
CREATE OR REPLACE FUNCTION notify_collaboration_change()
RETURNS TRIGGER AS $$
DECLARE
    v_notification JSONB;
    v_trip_name TEXT;
    v_added_by_email TEXT;
    v_user_email TEXT;
BEGIN
    -- Get trip details
    SELECT name INTO v_trip_name FROM trips WHERE id = NEW.trip_id;
    
    -- Get user emails for notification context
    SELECT email INTO v_added_by_email FROM users WHERE id = NEW.added_by;
    SELECT email INTO v_user_email FROM users WHERE id = NEW.user_id;
    
    -- Build notification payload
    v_notification := jsonb_build_object(
        'event_type', CASE 
            WHEN TG_OP = 'INSERT' THEN 'collaborator_added'
            WHEN TG_OP = 'UPDATE' THEN 'collaborator_updated'
            WHEN TG_OP = 'DELETE' THEN 'collaborator_removed'
        END,
        'trip_id', COALESCE(NEW.trip_id, OLD.trip_id),
        'trip_name', v_trip_name,
        'user_id', COALESCE(NEW.user_id, OLD.user_id),
        'user_email', v_user_email,
        'added_by', COALESCE(NEW.added_by, OLD.added_by),
        'added_by_email', v_added_by_email,
        'permission_level', COALESCE(NEW.permission_level, OLD.permission_level),
        'timestamp', NOW(),
        'operation', TG_OP
    );
    
    -- Send real-time notification
    PERFORM pg_notify('trip_collaboration', v_notification::TEXT);
    
    -- Log to audit trail
    INSERT INTO session_memories (
        session_id,
        user_id,
        content,
        metadata
    ) VALUES (
        '00000000-0000-0000-0000-000000000000'::UUID,
        COALESCE(NEW.added_by, OLD.added_by),
        format('Collaboration %s for trip: %s', 
            CASE TG_OP 
                WHEN 'INSERT' THEN 'added'
                WHEN 'UPDATE' THEN 'updated'
                WHEN 'DELETE' THEN 'removed'
            END,
            v_trip_name
        ),
        jsonb_build_object(
            'type', 'collaboration_audit',
            'event_data', v_notification
        )
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to validate collaboration permission hierarchy changes
CREATE OR REPLACE FUNCTION validate_collaboration_permissions()
RETURNS TRIGGER AS $$
DECLARE
    v_modifier_permission TEXT;
    v_is_owner BOOLEAN;
BEGIN
    -- Check if modifier is the trip owner
    SELECT user_id = NEW.added_by INTO v_is_owner
    FROM trips WHERE id = NEW.trip_id;
    
    IF NOT v_is_owner THEN
        -- Get modifier's permission level
        SELECT permission_level INTO v_modifier_permission
        FROM trip_collaborators
        WHERE trip_id = NEW.trip_id AND user_id = NEW.added_by;
        
        -- Non-owners can only add/modify collaborators with lower permissions
        IF v_modifier_permission IS NULL OR v_modifier_permission != 'admin' THEN
            RAISE EXCEPTION 'Insufficient permissions to modify collaborators';
        END IF;
        
        -- Admins cannot grant admin permissions
        IF NEW.permission_level = 'admin' AND v_modifier_permission = 'admin' THEN
            RAISE EXCEPTION 'Only trip owners can grant admin permissions';
        END IF;
    END IF;
    
    -- Prevent self-modification of permissions
    IF NEW.user_id = NEW.added_by AND TG_OP = 'UPDATE' THEN
        IF OLD.permission_level != NEW.permission_level THEN
            RAISE EXCEPTION 'Cannot modify your own permission level';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- CACHE INVALIDATION TRIGGER FUNCTIONS
-- ===========================

-- Function to notify cache invalidation needs
CREATE OR REPLACE FUNCTION notify_cache_invalidation()
RETURNS TRIGGER AS $$
DECLARE
    v_notification JSONB;
    v_table_name TEXT;
    v_record_id TEXT;
BEGIN
    v_table_name := TG_TABLE_NAME;
    
    -- Determine record ID based on table
    v_record_id := CASE 
        WHEN TG_TABLE_NAME IN ('trips', 'flights', 'accommodations', 'activities') 
            THEN COALESCE(NEW.id, OLD.id)::TEXT
        ELSE NULL
    END;
    
    -- Build cache invalidation notification
    v_notification := jsonb_build_object(
        'event_type', 'cache_invalidation',
        'table_name', v_table_name,
        'record_id', v_record_id,
        'operation', TG_OP,
        'timestamp', NOW()
    );
    
    -- Notify cache service
    PERFORM pg_notify('cache_invalidation', v_notification::TEXT);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup search cache on data changes
CREATE OR REPLACE FUNCTION cleanup_related_search_cache()
RETURNS TRIGGER AS $$
BEGIN
    -- When a trip is modified, clear related search cache
    IF TG_TABLE_NAME = 'trips' THEN
        -- Clear destination searches for the trip's destination
        DELETE FROM search_destinations 
        WHERE query_hash = md5(lower(trim(NEW.destination)))
        OR metadata->>'destination' = NEW.destination;
        
        -- Clear activity searches for the trip's destination
        DELETE FROM search_activities
        WHERE destination = NEW.destination;
    END IF;
    
    -- When accommodations are modified, clear hotel searches
    IF TG_TABLE_NAME = 'accommodations' THEN
        DELETE FROM search_hotels
        WHERE location = NEW.location
        AND check_in_date = NEW.check_in_date;
    END IF;
    
    -- When flights are modified, clear flight searches
    IF TG_TABLE_NAME = 'flights' THEN
        DELETE FROM search_flights
        WHERE origin = NEW.origin
        AND destination = NEW.destination
        AND departure_date::DATE = NEW.departure_time::DATE;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- BUSINESS LOGIC TRIGGER FUNCTIONS
-- ===========================

-- Function to auto-expire inactive chat sessions
CREATE OR REPLACE FUNCTION auto_expire_chat_session()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if session has been inactive for configured timeout (default 24 hours)
    IF NEW.updated_at < NOW() - INTERVAL '24 hours' AND NEW.ended_at IS NULL THEN
        NEW.ended_at := NOW();
        
        -- Notify about session expiration
        PERFORM pg_notify('chat_session_expired', 
            jsonb_build_object(
                'session_id', NEW.id,
                'user_id', NEW.user_id,
                'trip_id', NEW.trip_id,
                'expired_at', NOW()
            )::TEXT
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up orphaned file attachments
CREATE OR REPLACE FUNCTION cleanup_orphaned_attachments()
RETURNS TRIGGER AS $$
DECLARE
    v_attachment_ids UUID[];
BEGIN
    -- When a chat message is deleted, mark its attachments for cleanup
    IF TG_OP = 'DELETE' AND OLD.metadata ? 'attachments' THEN
        -- Extract attachment IDs from metadata
        SELECT array_agg((attachment->>'id')::UUID)
        INTO v_attachment_ids
        FROM jsonb_array_elements(OLD.metadata->'attachments') AS attachment;
        
        -- Mark attachments as orphaned (soft delete)
        UPDATE file_attachments
        SET metadata = jsonb_set(
            COALESCE(metadata, '{}'::jsonb),
            '{orphaned}',
            'true'::jsonb
        )
        WHERE id = ANY(v_attachment_ids);
    END IF;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Function to update trip status based on bookings
CREATE OR REPLACE FUNCTION update_trip_status_from_bookings()
RETURNS TRIGGER AS $$
DECLARE
    v_trip_id BIGINT;
    v_has_bookings BOOLEAN;
    v_all_confirmed BOOLEAN;
    v_any_cancelled BOOLEAN;
BEGIN
    -- Get trip ID based on table
    v_trip_id := CASE 
        WHEN TG_TABLE_NAME = 'flights' THEN NEW.trip_id
        WHEN TG_TABLE_NAME = 'accommodations' THEN NEW.trip_id
        ELSE NULL
    END;
    
    IF v_trip_id IS NULL THEN
        RETURN NEW;
    END IF;
    
    -- Check booking statuses
    SELECT 
        COUNT(*) > 0,
        COUNT(*) FILTER (WHERE booking_status != 'confirmed') = 0,
        COUNT(*) FILTER (WHERE booking_status = 'cancelled') > 0
    INTO v_has_bookings, v_all_confirmed, v_any_cancelled
    FROM (
        SELECT booking_status FROM flights WHERE trip_id = v_trip_id
        UNION ALL
        SELECT booking_status FROM accommodations WHERE trip_id = v_trip_id
    ) bookings;
    
    -- Update trip status accordingly
    IF v_has_bookings THEN
        IF v_any_cancelled THEN
            UPDATE trips SET status = 'needs_attention' WHERE id = v_trip_id;
        ELSIF v_all_confirmed THEN
            UPDATE trips SET status = 'confirmed' WHERE id = v_trip_id;
        ELSE
            UPDATE trips SET status = 'in_progress' WHERE id = v_trip_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to maintain collaboration audit trail
CREATE OR REPLACE FUNCTION audit_collaboration_changes()
RETURNS TRIGGER AS $$
DECLARE
    v_changes JSONB;
BEGIN
    -- Track what changed in collaborations
    IF TG_OP = 'UPDATE' THEN
        v_changes := jsonb_build_object();
        
        IF OLD.permission_level IS DISTINCT FROM NEW.permission_level THEN
            v_changes := v_changes || jsonb_build_object(
                'permission_level', jsonb_build_object(
                    'old', OLD.permission_level,
                    'new', NEW.permission_level
                )
            );
        END IF;
        
        -- Store audit record
        INSERT INTO session_memories (
            session_id,
            user_id,
            content,
            metadata
        ) VALUES (
            '00000000-0000-0000-0000-000000000000'::UUID,
            NEW.added_by,
            format('Collaboration updated for trip %s', NEW.trip_id),
            jsonb_build_object(
                'type', 'collaboration_audit',
                'operation', 'UPDATE',
                'trip_id', NEW.trip_id,
                'user_id', NEW.user_id,
                'changes', v_changes,
                'timestamp', NOW()
            )
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- SCHEDULED JOB FUNCTIONS (for pg_cron)
-- ===========================

-- Daily cleanup job function
CREATE OR REPLACE FUNCTION daily_cleanup_job()
RETURNS VOID AS $$
DECLARE
    v_expired_sessions INT;
    v_orphaned_attachments INT;
    v_expired_cache INT;
    v_old_memories INT;
BEGIN
    -- Expire inactive sessions
    SELECT expire_inactive_sessions(24) INTO v_expired_sessions;
    
    -- Clean up truly orphaned attachments (older than 7 days)
    DELETE FROM file_attachments
    WHERE (metadata->>'orphaned')::BOOLEAN = true
    AND created_at < NOW() - INTERVAL '7 days';
    GET DIAGNOSTICS v_orphaned_attachments = ROW_COUNT;
    
    -- Clean up expired search cache
    SELECT SUM(deleted_count) INTO v_expired_cache
    FROM cleanup_expired_search_cache();
    
    -- Clean up old session memories
    SELECT cleanup_expired_session_memories(168) INTO v_old_memories; -- 7 days
    
    -- Log cleanup results
    INSERT INTO session_memories (
        session_id,
        user_id,
        content,
        metadata
    ) VALUES (
        '00000000-0000-0000-0000-000000000000'::UUID,
        '00000000-0000-0000-0000-000000000001'::UUID,
        'Daily cleanup completed',
        jsonb_build_object(
            'type', 'maintenance',
            'job', 'daily_cleanup',
            'results', jsonb_build_object(
                'expired_sessions', v_expired_sessions,
                'orphaned_attachments', v_orphaned_attachments,
                'expired_cache', v_expired_cache,
                'old_memories', v_old_memories
            ),
            'timestamp', NOW()
        )
    );
END;
$$ LANGUAGE plpgsql;

-- Weekly performance maintenance job
CREATE OR REPLACE FUNCTION weekly_maintenance_job()
RETURNS VOID AS $$
BEGIN
    -- Run maintenance
    PERFORM maintain_database_performance();
    
    -- Clean up orphaned collaborators
    PERFORM cleanup_orphaned_collaborators();
    
    -- Optimize indexes if needed
    PERFORM optimize_vector_indexes();
    
    -- Log completion
    INSERT INTO session_memories (
        session_id,
        user_id,
        content,
        metadata
    ) VALUES (
        '00000000-0000-0000-0000-000000000000'::UUID,
        '00000000-0000-0000-0000-000000000001'::UUID,
        'Weekly maintenance completed',
        jsonb_build_object(
            'type', 'maintenance',
            'job', 'weekly_maintenance',
            'timestamp', NOW()
        )
    );
END;
$$ LANGUAGE plpgsql;

-- Monthly deep cleanup job
CREATE OR REPLACE FUNCTION monthly_cleanup_job()
RETURNS VOID AS $$
DECLARE
    v_old_memories INT;
    v_collaboration_stats RECORD;
BEGIN
    -- Deep clean old memories (keep last year only)
    SELECT cleanup_old_memories(365, 1000) INTO v_old_memories;
    
    -- Get collaboration statistics before cleanup
    SELECT * INTO v_collaboration_stats FROM get_collaboration_statistics();
    
    -- Clean up old audit logs (keep 6 months)
    DELETE FROM session_memories
    WHERE metadata->>'type' IN ('collaboration_audit', 'maintenance')
    AND created_at < NOW() - INTERVAL '6 months';
    
    -- Log results
    INSERT INTO session_memories (
        session_id,
        user_id,
        content,
        metadata
    ) VALUES (
        '00000000-0000-0000-0000-000000000000'::UUID,
        '00000000-0000-0000-0000-000000000001'::UUID,
        'Monthly deep cleanup completed',
        jsonb_build_object(
            'type', 'maintenance',
            'job', 'monthly_cleanup',
            'results', jsonb_build_object(
                'old_memories_cleaned', v_old_memories,
                'collaboration_stats', to_jsonb(v_collaboration_stats)
            ),
            'timestamp', NOW()
        )
    );
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- 04_triggers.sql
-- ===========================

-- Database Triggers Schema
-- Description: Automated database operations and data integrity triggers
-- Dependencies: 01_tables.sql (table definitions), 03_functions.sql (trigger functions)

-- ===========================
-- UPDATED_AT TRIGGERS
-- ===========================

-- Create triggers for updated_at columns (automatic timestamp updates)
CREATE TRIGGER update_trips_updated_at 
    BEFORE UPDATE ON trips 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_flights_updated_at 
    BEFORE UPDATE ON flights 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_accommodations_updated_at 
    BEFORE UPDATE ON accommodations 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_sessions_updated_at 
    BEFORE UPDATE ON chat_sessions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memories_updated_at 
    BEFORE UPDATE ON memories 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add triggers for new tables with updated_at columns
CREATE TRIGGER update_file_attachments_updated_at 
    BEFORE UPDATE ON file_attachments 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trip_collaborators_updated_at 
    BEFORE UPDATE ON trip_collaborators 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_itinerary_items_updated_at 
    BEFORE UPDATE ON itinerary_items 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transportation_updated_at 
    BEFORE UPDATE ON transportation 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'trip_notes'
  ) THEN
    EXECUTE 'CREATE TRIGGER IF NOT EXISTS update_trip_notes_updated_at '
         || 'BEFORE UPDATE ON trip_notes '
         || 'FOR EACH ROW '
         || 'EXECUTE FUNCTION update_updated_at_column()';
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'saved_options'
  ) THEN
    EXECUTE 'CREATE TRIGGER IF NOT EXISTS update_saved_options_updated_at '
         || 'BEFORE UPDATE ON saved_options '
         || 'FOR EACH ROW '
         || 'EXECUTE FUNCTION update_updated_at_column()';
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'trip_comparisons'
  ) THEN
    EXECUTE 'CREATE TRIGGER IF NOT EXISTS update_trip_comparisons_updated_at '
         || 'BEFORE UPDATE ON trip_comparisons '
         || 'FOR EACH ROW '
         || 'EXECUTE FUNCTION update_updated_at_column()';
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'price_history'
  ) THEN
    EXECUTE 'CREATE TRIGGER IF NOT EXISTS update_price_history_updated_at '
         || 'BEFORE UPDATE ON price_history '
         || 'FOR EACH ROW '
         || 'EXECUTE FUNCTION update_updated_at_column()';
  END IF;
END $$;

-- ===========================
-- COLLABORATION EVENT TRIGGERS
-- ===========================

-- Trigger for collaboration changes notifications
CREATE TRIGGER notify_trip_collaboration_changes
    AFTER INSERT OR UPDATE OR DELETE ON trip_collaborators
    FOR EACH ROW
    EXECUTE FUNCTION notify_collaboration_change();

-- Trigger to validate collaboration permissions
CREATE TRIGGER validate_collaboration_permissions_trigger
    BEFORE INSERT OR UPDATE ON trip_collaborators
    FOR EACH ROW
    EXECUTE FUNCTION validate_collaboration_permissions();

-- Trigger to audit collaboration changes
CREATE TRIGGER audit_trip_collaboration_changes
    AFTER UPDATE ON trip_collaborators
    FOR EACH ROW
    EXECUTE FUNCTION audit_collaboration_changes();

-- ===========================
-- CACHE INVALIDATION TRIGGERS
-- ===========================

-- Cache invalidation notifications for main entities
CREATE TRIGGER notify_trips_cache_invalidation
    AFTER INSERT OR UPDATE OR DELETE ON trips
    FOR EACH ROW
    EXECUTE FUNCTION notify_cache_invalidation();

CREATE TRIGGER notify_flights_cache_invalidation
    AFTER INSERT OR UPDATE OR DELETE ON flights
    FOR EACH ROW
    EXECUTE FUNCTION notify_cache_invalidation();

CREATE TRIGGER notify_accommodations_cache_invalidation
    AFTER INSERT OR UPDATE OR DELETE ON accommodations
    FOR EACH ROW
    EXECUTE FUNCTION notify_cache_invalidation();

-- Search cache cleanup triggers
CREATE TRIGGER cleanup_search_cache_on_trip_change
    AFTER INSERT OR UPDATE ON trips
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_related_search_cache();

CREATE TRIGGER cleanup_search_cache_on_accommodation_change
    AFTER INSERT OR UPDATE ON accommodations
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_related_search_cache();

CREATE TRIGGER cleanup_search_cache_on_flight_change
    AFTER INSERT OR UPDATE ON flights
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_related_search_cache();

-- ===========================
-- BUSINESS LOGIC TRIGGERS
-- ===========================

-- Auto-expire inactive chat sessions
CREATE TRIGGER auto_expire_inactive_sessions
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    WHEN (NEW.updated_at IS DISTINCT FROM OLD.updated_at)
    EXECUTE FUNCTION auto_expire_chat_session();

-- Clean up orphaned attachments when messages are deleted
CREATE TRIGGER cleanup_message_attachments
    AFTER DELETE ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_orphaned_attachments();

-- Update trip status based on booking changes
-- Split triggers to avoid TG_OP in WHEN
CREATE TRIGGER update_trip_status_from_flight_bookings_ins
    AFTER INSERT ON flights
    FOR EACH ROW
    EXECUTE FUNCTION update_trip_status_from_bookings();

CREATE TRIGGER update_trip_status_from_flight_bookings_upd
    AFTER UPDATE ON flights
    FOR EACH ROW
    WHEN (NEW.booking_status IS DISTINCT FROM OLD.booking_status)
    EXECUTE FUNCTION update_trip_status_from_bookings();

CREATE TRIGGER update_trip_status_from_accommodation_bookings_ins
    AFTER INSERT ON accommodations
    FOR EACH ROW
    EXECUTE FUNCTION update_trip_status_from_bookings();

CREATE TRIGGER update_trip_status_from_accommodation_bookings_upd
    AFTER UPDATE ON accommodations
    FOR EACH ROW
    WHEN (NEW.booking_status IS DISTINCT FROM OLD.booking_status)
    EXECUTE FUNCTION update_trip_status_from_bookings();

-- ===========================
-- PG_CRON SCHEDULED JOBS
-- ===========================

-- Note: These jobs need to be scheduled using pg_cron extension
-- Run these commands as superuser after enabling pg_cron:

-- Schedule daily cleanup (runs at 2 AM UTC)
-- SELECT cron.schedule('daily-cleanup', '0 2 * * *', 'SELECT daily_cleanup_job();');

-- Schedule weekly maintenance (runs Sunday at 3 AM UTC)
-- SELECT cron.schedule('weekly-maintenance', '0 3 * * 0', 'SELECT weekly_maintenance_job();');

-- Schedule monthly deep cleanup (runs on the 1st at 4 AM UTC)
-- SELECT cron.schedule('monthly-cleanup', '0 4 1 * *', 'SELECT monthly_cleanup_job();');

-- Schedule search cache cleanup (runs every 6 hours)
-- SELECT cron.schedule('search-cache-cleanup', '0 */6 * * *', 'SELECT cleanup_expired_search_cache();');

-- Schedule session expiration check (runs every hour)
-- SELECT cron.schedule('expire-sessions', '0 * * * *', 'SELECT expire_inactive_sessions(24);');

-- ===========================
-- 05_policies.sql
-- ===========================

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

-- Memory tables (now using UUID user_id with proper foreign key constraints)
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_memories ENABLE ROW LEVEL SECURITY;

-- ===========================
-- CORE BUSINESS LOGIC POLICIES
-- ===========================

-- API Keys: Users can only manage their own API keys
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

-- ===========================
-- 06_views.sql
-- ===========================

-- Database Views Schema
-- Description: Commonly used database views for efficient querying
-- Dependencies: 01_tables.sql (all table definitions)

-- ===========================
-- CHAT SYSTEM VIEWS
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

-- ===========================
-- TRIP MANAGEMENT VIEWS
-- ===========================

-- Create view for trip summaries with related data counts and costs
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

-- Create view for user trip statistics
CREATE OR REPLACE VIEW user_trip_stats AS
SELECT 
    user_id,
    COUNT(*) as total_trips,
    COUNT(CASE WHEN status = 'planning' THEN 1 END) as planning_trips,
    COUNT(CASE WHEN status = 'booked' THEN 1 END) as booked_trips,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_trips,
    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_trips,
    AVG(budget) as average_budget,
    SUM(budget) as total_budget,
    MIN(created_at) as first_trip_created,
    MAX(created_at) as last_trip_created
FROM trips
GROUP BY user_id;

-- ===========================
-- BOOKING STATUS VIEWS
-- ===========================

-- Create view for upcoming bookings (flights and accommodations)
CREATE OR REPLACE VIEW upcoming_bookings AS
SELECT 
    'flight' as booking_type,
    f.id::TEXT as booking_id,
    t.user_id,
    t.id as trip_id,
    t.name as trip_name,
    f.origin || ' → ' || f.destination as description,
    f.departure_date as booking_date,
    f.price,
    f.currency,
    f.booking_status
FROM flights f
JOIN trips t ON f.trip_id = t.id
WHERE f.departure_date >= CURRENT_DATE
    AND f.booking_status IN ('reserved', 'booked')

UNION ALL

SELECT 
    'accommodation' as booking_type,
    a.id::TEXT as booking_id,
    t.user_id,
    t.id as trip_id,
    t.name as trip_name,
    a.name as description,
    a.check_in_date as booking_date,
    a.total_price as price,
    a.currency,
    a.booking_status
FROM accommodations a
JOIN trips t ON a.trip_id = t.id
WHERE a.check_in_date >= CURRENT_DATE
    AND a.booking_status IN ('reserved', 'booked')

ORDER BY booking_date ASC;

-- ===========================
-- API USAGE VIEWS
-- ===========================

-- Create view for active API keys by service
SELECT 
    service_name,
    COUNT(*) as total_keys,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_keys,
    COUNT(CASE WHEN last_used_at IS NOT NULL THEN 1 END) as used_keys,
    MAX(last_used_at) as last_usage,
    COUNT(CASE WHEN expires_at IS NOT NULL AND expires_at < NOW() THEN 1 END) as expired_keys
GROUP BY service_name
ORDER BY total_keys DESC;

-- Create view for user API key status
SELECT 
    user_id,
    COUNT(*) as total_keys,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_keys,
    array_agg(DISTINCT service_name) as services,
    MIN(created_at) as first_key_added,
    MAX(last_used_at) as last_api_usage
GROUP BY user_id;

-- ===========================
-- MEMORY SYSTEM VIEWS
-- ===========================

-- Create view for memory statistics by user
CREATE OR REPLACE VIEW user_memory_stats AS
SELECT 
    user_id,
    COUNT(*) as total_memories,
    COUNT(CASE WHEN memory_type = 'user_preference' THEN 1 END) as preference_memories,
    COUNT(CASE WHEN memory_type = 'trip_history' THEN 1 END) as trip_history_memories,
    COUNT(CASE WHEN memory_type = 'search_pattern' THEN 1 END) as search_pattern_memories,
    COUNT(CASE WHEN memory_type = 'conversation_context' THEN 1 END) as conversation_memories,
    MIN(created_at) as first_memory,
    MAX(updated_at) as last_memory_update
FROM memories
GROUP BY user_id;

-- ===========================
-- VIEW COMMENTS
-- ===========================

COMMENT ON VIEW active_chat_sessions IS 'Active chat sessions with message count and last activity';
COMMENT ON VIEW trip_summaries IS 'Trip overview with associated bookings count and total costs';
COMMENT ON VIEW user_trip_stats IS 'User-level trip statistics and spending patterns';
COMMENT ON VIEW upcoming_bookings IS 'All upcoming confirmed bookings (flights and accommodations)';
COMMENT ON VIEW user_memory_stats IS 'User memory system usage and categorization statistics';

-- ===========================
-- 07_automation.sql
-- ===========================

-- Automated Maintenance and Scheduled Jobs
-- Description: pg_cron scheduled jobs for automated database maintenance
-- Dependencies: 00_extensions.sql (pg_cron), 01_tables.sql, 03_functions.sql

-- ===========================
-- CLEANUP JOBS
-- ===========================

-- Remove expired cache entries daily
SELECT cron.schedule(
    'cleanup-expired-search-cache',
    '0 2 * * *', -- Run at 2 AM daily
    $$
    DELETE FROM search_destinations WHERE expires_at < NOW();
    DELETE FROM search_activities WHERE expires_at < NOW();
    DELETE FROM search_flights WHERE expires_at < NOW();
    DELETE FROM search_hotels WHERE expires_at < NOW();
    $$
);

-- Clean up old session memories (older than 30 days)
SELECT cron.schedule(
    'cleanup-old-session-memories',
    '0 3 * * *', -- Run at 3 AM daily
    $$
    DELETE FROM session_memories 
    WHERE created_at < NOW() - INTERVAL '30 days';
    $$
);

-- Archive completed trips older than 1 year
SELECT cron.schedule(
    'archive-old-completed-trips',
    '0 4 * * 0', -- Run at 4 AM every Sunday
    $$
    UPDATE trips 
    SET status = 'archived'
    WHERE status = 'completed' 
    AND updated_at < NOW() - INTERVAL '1 year';
    $$
);

-- ===========================
-- PERFORMANCE OPTIMIZATION JOBS
-- ===========================

-- Update table statistics for query optimization
SELECT cron.schedule(
    'update-table-statistics',
    '0 1 * * *', -- Run at 1 AM daily
    $$
    ANALYZE trips;
    ANALYZE flights;
    ANALYZE accommodations;
    ANALYZE chat_messages;
    ANALYZE memories;
    ANALYZE search_destinations;
    ANALYZE search_activities;
    ANALYZE search_flights;
    ANALYZE search_hotels;
    $$
);

-- Vacuum tables to reclaim storage
SELECT cron.schedule(
    'vacuum-tables',
    '0 5 * * 0', -- Run at 5 AM every Sunday
    $$
    VACUUM ANALYZE trips;
    VACUUM ANALYZE flights;
    VACUUM ANALYZE accommodations;
    VACUUM ANALYZE chat_messages;
    VACUUM ANALYZE memories;
    $$
);

-- ===========================
-- MONITORING JOBS
-- ===========================

-- Monitor API key usage and send alerts for expiring keys
SELECT cron.schedule(
    'monitor-expiring-api-keys',
    '0 9 * * *', -- Run at 9 AM daily
    $$
    INSERT INTO notifications (user_id, type, title, message, metadata)
    SELECT 
        user_id,
        'API Key Expiring Soon',
        format('Your %s API key "%s" will expire in %s days', 
               service_name, key_name, 
               EXTRACT(DAY FROM expires_at - NOW())::TEXT),
        jsonb_build_object(
            'service_name', service_name,
            'key_name', key_name,
            'expires_at', expires_at
        )
    WHERE is_active = true
    AND expires_at IS NOT NULL
    AND expires_at BETWEEN NOW() AND NOW() + INTERVAL '7 days'
    AND NOT EXISTS (
        SELECT 1 FROM notifications n
        AND n.created_at > NOW() - INTERVAL '7 days'
    );
    $$
);

-- ===========================
-- WEBHOOK NOTIFICATION FUNCTIONS
-- ===========================

-- Function to send webhook notifications using pg_net
CREATE OR REPLACE FUNCTION send_webhook_notification(
    webhook_url TEXT,
    event_type TEXT,
    payload JSONB
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    request_id BIGINT;
BEGIN
    SELECT net.http_post(
        url := webhook_url,
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'X-Event-Type', event_type,
            'X-Timestamp', EXTRACT(EPOCH FROM NOW())::TEXT
        ),
        body := payload::TEXT
    ) INTO request_id;
    
    RETURN request_id;
END;
$$;

-- Function to notify Edge Functions of trip updates
CREATE OR REPLACE FUNCTION notify_trip_update()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    edge_function_url TEXT;
    notification_payload JSONB;
BEGIN
    -- Get Edge Function URL from environment or config
    edge_function_url := current_setting('app.edge_function_url', true);
    
    IF edge_function_url IS NOT NULL THEN
        notification_payload := jsonb_build_object(
            'event', TG_OP,
            'table', TG_TABLE_NAME,
            'trip_id', NEW.id,
            'user_id', NEW.user_id,
            'timestamp', NOW(),
            'changes', CASE 
                WHEN TG_OP = 'UPDATE' THEN 
                    jsonb_build_object(
                        'old', row_to_json(OLD),
                        'new', row_to_json(NEW)
                    )
                ELSE row_to_json(NEW)
            END
        );
        
        PERFORM send_webhook_notification(
            edge_function_url,
            'trip.' || lower(TG_OP),
            notification_payload
        );
    END IF;
    
    RETURN NEW;
END;
$$;

-- ===========================
-- DATA AGGREGATION JOBS
-- ===========================

-- Update trip statistics daily
SELECT cron.schedule(
    'update-trip-statistics',
    '0 6 * * *', -- Run at 6 AM daily
    $$
    -- Create or update materialized view for trip statistics
    REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS trip_statistics;
    $$
);

-- Generate memory embeddings for new content
SELECT cron.schedule(
    'generate-memory-embeddings',
    '*/30 * * * *', -- Run every 30 minutes
    $$
    -- This would typically call an Edge Function to generate embeddings
    -- For now, we'll mark memories that need embedding
    UPDATE memories 
    SET metadata = jsonb_set(
        COALESCE(metadata, '{}'),
        '{needs_embedding}',
        'true'
    )
    WHERE embedding IS NULL
    AND created_at > NOW() - INTERVAL '1 hour';
    $$
);

-- ===========================
-- HEALTH CHECK JOBS
-- ===========================

-- Monitor database health and connections
SELECT cron.schedule(
    'monitor-database-health',
    '*/5 * * * *', -- Run every 5 minutes
    $$
    INSERT INTO system_metrics (metric_type, metric_name, value, metadata)
    SELECT 
        'database',
        'active_connections',
        count(*),
        jsonb_build_object(
            'by_state', jsonb_object_agg(state, count),
            'by_application', jsonb_object_agg(application_name, count)
        )
    FROM pg_stat_activity
    WHERE datname = current_database()
    GROUP BY ROLLUP(state), ROLLUP(application_name);
    $$
);

-- ===========================
-- JOB MANAGEMENT FUNCTIONS
-- ===========================

-- Function to list all scheduled jobs
CREATE OR REPLACE FUNCTION list_scheduled_jobs()
RETURNS TABLE (
    jobid BIGINT,
    schedule TEXT,
    command TEXT,
    nodename TEXT,
    nodeport INTEGER,
    database TEXT,
    username TEXT,
    active BOOLEAN
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT 
        jobid,
        schedule,
        command,
        nodename,
        nodeport,
        database,
        username,
        active
    FROM cron.job
    ORDER BY jobid;
$$;

-- Function to get job execution history
CREATE OR REPLACE FUNCTION get_job_history(
    job_name TEXT DEFAULT NULL,
    limit_rows INTEGER DEFAULT 100
)
RETURNS TABLE (
    jobid BIGINT,
    job_name TEXT,
    status TEXT,
    return_message TEXT,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    duration INTERVAL
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT 
        d.jobid,
        j.jobname,
        d.status,
        d.return_message,
        d.start_time,
        d.end_time,
        d.end_time - d.start_time AS duration
    FROM cron.job_run_details d
    JOIN cron.job j ON j.jobid = d.jobid
    WHERE (job_name IS NULL OR j.jobname = job_name)
    ORDER BY d.start_time DESC
    LIMIT limit_rows;
$$;

-- ===========================
-- MONITORING TABLES
-- ===========================

-- Create notifications table if it doesn't exist
CREATE TABLE IF NOT EXISTS notifications (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create system metrics table for monitoring
CREATE TABLE IF NOT EXISTS system_metrics (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    metric_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value NUMERIC NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread 
ON notifications(user_id, read) 
WHERE read = false;

CREATE INDEX IF NOT EXISTS idx_system_metrics_type_time 
ON system_metrics(metric_type, created_at DESC);

-- ===========================
-- 08_webhooks.sql
-- ===========================

-- Webhook Integration Functions
-- Description: pg_net based webhook functions for external service integration
-- Dependencies: 00_extensions.sql (pg_net), 01_tables.sql

-- ===========================
-- WEBHOOK CONFIGURATION TABLE
-- ===========================

-- Create table to store webhook configurations
CREATE TABLE IF NOT EXISTS webhook_configs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    secret TEXT,
    events TEXT[] NOT NULL,
    headers JSONB DEFAULT '{}',
    retry_config JSONB DEFAULT '{"max_retries": 3, "retry_delay": 1000}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create webhook logs table
CREATE TABLE IF NOT EXISTS webhook_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    webhook_config_id BIGINT REFERENCES webhook_configs(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    response_status INTEGER,
    response_body TEXT,
    attempt_count INTEGER DEFAULT 1,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- ===========================
-- CORE WEBHOOK FUNCTIONS
-- ===========================

-- Function to send webhook with retry logic
CREATE OR REPLACE FUNCTION send_webhook_with_retry(
    p_webhook_name TEXT,
    p_event_type TEXT,
    p_payload JSONB,
    p_attempt INTEGER DEFAULT 1
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_webhook webhook_configs;
    v_request_id BIGINT;
    v_headers JSONB;
    v_log_id BIGINT;
BEGIN
    -- Get webhook configuration
    SELECT * INTO v_webhook
    FROM webhook_configs
    WHERE name = p_webhook_name
    AND is_active = TRUE
    AND p_event_type = ANY(events);
    
    IF v_webhook IS NULL THEN
        RAISE EXCEPTION 'Webhook % not found or not active for event %', p_webhook_name, p_event_type;
    END IF;
    
    -- Prepare headers
    v_headers := v_webhook.headers || jsonb_build_object(
        'Content-Type', 'application/json',
        'X-Webhook-Event', p_event_type,
        'X-Webhook-Timestamp', EXTRACT(EPOCH FROM NOW())::TEXT,
        'X-Webhook-Attempt', p_attempt::TEXT
    );
    
    -- Add signature if secret is configured
    IF v_webhook.secret IS NOT NULL THEN
        v_headers := v_headers || jsonb_build_object(
            'X-Webhook-Signature', 
            encode(
                hmac(p_payload::TEXT, v_webhook.secret, 'sha256'),
                'hex'
            )
        );
    END IF;
    
    -- Log the webhook attempt
    INSERT INTO webhook_logs (
        webhook_config_id,
        event_type,
        payload,
        attempt_count
    ) VALUES (
        v_webhook.id,
        p_event_type,
        p_payload,
        p_attempt
    ) RETURNING id INTO v_log_id;
    
    -- Send the webhook
    SELECT net.http_post(
        url := v_webhook.url,
        headers := v_headers,
        body := p_payload::TEXT,
        timeout_milliseconds := 30000
    ) INTO v_request_id;
    
    -- Schedule retry check if configured
    IF p_attempt < (v_webhook.retry_config->>'max_retries')::INTEGER THEN
        PERFORM pg_sleep((v_webhook.retry_config->>'retry_delay')::FLOAT / 1000);
        -- This would typically be handled by a separate process
        -- For now, we'll log the request ID for manual retry
    END IF;
    
    RETURN v_request_id;
END;
$$;

-- ===========================
-- EVENT-SPECIFIC WEBHOOK FUNCTIONS
-- ===========================

-- Webhook for trip collaboration events
CREATE OR REPLACE FUNCTION webhook_trip_collaboration()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_payload JSONB;
    v_event_type TEXT;
BEGIN
    -- Determine event type
    v_event_type := CASE TG_OP
        WHEN 'INSERT' THEN 'trip.collaborator.added'
        WHEN 'UPDATE' THEN 'trip.collaborator.updated'
        WHEN 'DELETE' THEN 'trip.collaborator.removed'
    END;
    
    -- Build payload
    v_payload := jsonb_build_object(
        'event', v_event_type,
        'trip_id', COALESCE(NEW.trip_id, OLD.trip_id),
        'user_id', COALESCE(NEW.user_id, OLD.user_id),
        'added_by', COALESCE(NEW.added_by, OLD.added_by),
        'permission_level', COALESCE(NEW.permission_level, OLD.permission_level),
        'timestamp', NOW(),
        'operation', TG_OP,
        'data', CASE
            WHEN TG_OP = 'DELETE' THEN row_to_json(OLD)
            ELSE row_to_json(NEW)
        END
    );
    
    -- Send webhooks to all configured endpoints
    PERFORM send_webhook_with_retry('trip_events', v_event_type, v_payload);
    
    RETURN COALESCE(NEW, OLD);
END;
$$;

-- Webhook for chat message events
CREATE OR REPLACE FUNCTION webhook_chat_message()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_payload JSONB;
    v_session RECORD;
BEGIN
    -- Get session details
    SELECT 
        cs.user_id,
        cs.trip_id,
        cs.metadata
    INTO v_session
    FROM chat_sessions cs
    WHERE cs.id = NEW.session_id;
    
    -- Build payload
    v_payload := jsonb_build_object(
        'event', 'chat.message.created',
        'message_id', NEW.id,
        'session_id', NEW.session_id,
        'user_id', v_session.user_id,
        'trip_id', v_session.trip_id,
        'role', NEW.role,
        'timestamp', NEW.created_at,
        'metadata', NEW.metadata
    );
    
    -- Send webhook
    PERFORM send_webhook_with_retry('chat_events', 'chat.message.created', v_payload);
    
    -- Trigger Edge Function for AI processing if needed
    IF NEW.role = 'user' THEN
        PERFORM send_webhook_with_retry('ai_processing', 'chat.message.process', 
            v_payload || jsonb_build_object('content', NEW.content)
        );
    END IF;
    
    RETURN NEW;
END;
$$;

-- Webhook for booking status changes
CREATE OR REPLACE FUNCTION webhook_booking_status()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_payload JSONB;
    v_trip RECORD;
    v_table_name TEXT;
    v_old_status TEXT;
    v_new_status TEXT;
BEGIN
    -- Get table name and status values
    v_table_name := TG_TABLE_NAME;
    v_old_status := CASE WHEN TG_OP = 'UPDATE' THEN OLD.booking_status ELSE NULL END;
    v_new_status := NEW.booking_status;
    
    -- Skip if status hasn't changed on update
    IF TG_OP = 'UPDATE' AND v_old_status = v_new_status THEN
        RETURN NEW;
    END IF;
    
    -- Get trip details
    SELECT 
        t.user_id,
        t.name,
        t.destination
    INTO v_trip
    FROM trips t
    WHERE t.id = NEW.trip_id;
    
    -- Build payload
    v_payload := jsonb_build_object(
        'event', format('booking.%s.%s', v_table_name, v_new_status),
        'booking_type', v_table_name,
        'booking_id', NEW.id,
        'trip_id', NEW.trip_id,
        'user_id', v_trip.user_id,
        'old_status', v_old_status,
        'new_status', v_new_status,
        'timestamp', NOW(),
        'details', row_to_json(NEW)
    );
    
    -- Send webhook
    PERFORM send_webhook_with_retry('booking_events', 
        format('booking.%s.%s', v_table_name, v_new_status), 
        v_payload
    );
    
    -- Send notification webhook if booking is confirmed
    IF v_new_status = 'booked' THEN
        PERFORM send_webhook_with_retry('notification_service', 
            'booking.confirmed', 
            v_payload || jsonb_build_object(
                'trip_name', v_trip.name,
                'destination', v_trip.destination
            )
        );
    END IF;
    
    RETURN NEW;
END;
$$;

-- ===========================
-- EXTERNAL SERVICE INTEGRATIONS
-- ===========================

-- Function to sync with external calendar services
CREATE OR REPLACE FUNCTION sync_to_calendar(
    p_user_id UUID,
    p_trip_id BIGINT,
    p_calendar_service TEXT
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_trip RECORD;
    v_items JSONB;
    v_payload JSONB;
    v_request_id BIGINT;
BEGIN
    -- Get trip details
    SELECT * INTO v_trip
    FROM trips
    WHERE id = p_trip_id AND user_id = p_user_id;
    
    IF v_trip IS NULL THEN
        RAISE EXCEPTION 'Trip not found';
    END IF;
    
    -- Get all itinerary items
    SELECT jsonb_agg(
        jsonb_build_object(
            'title', title,
            'description', description,
            'start_time', start_time,
            'end_time', end_time,
            'location', location
        ) ORDER BY start_time
    ) INTO v_items
    FROM itinerary_items
    WHERE trip_id = p_trip_id;
    
    -- Build calendar sync payload
    v_payload := jsonb_build_object(
        'user_id', p_user_id,
        'trip_id', p_trip_id,
        'calendar_service', p_calendar_service,
        'trip_name', v_trip.name,
        'start_date', v_trip.start_date,
        'end_date', v_trip.end_date,
        'destination', v_trip.destination,
        'items', COALESCE(v_items, '[]'::JSONB)
    );
    
    -- Send to calendar sync service
    v_request_id := send_webhook_with_retry(
        'calendar_sync',
        'calendar.sync.request',
        v_payload
    );
    
    RETURN v_request_id;
END;
$$;

-- ===========================
-- WEBHOOK TRIGGERS
-- ===========================

-- Create triggers for webhook events
CREATE TRIGGER webhook_trip_collaborator_events
AFTER INSERT OR UPDATE OR DELETE ON trip_collaborators
FOR EACH ROW EXECUTE FUNCTION webhook_trip_collaboration();

CREATE TRIGGER webhook_chat_message_events
AFTER INSERT ON chat_messages
FOR EACH ROW EXECUTE FUNCTION webhook_chat_message();

-- Split to avoid OLD on INSERT
CREATE TRIGGER webhook_flight_booking_events_ins
AFTER INSERT ON flights
FOR EACH ROW 
EXECUTE FUNCTION webhook_booking_status();

CREATE TRIGGER webhook_flight_booking_events_upd
AFTER UPDATE ON flights
FOR EACH ROW 
WHEN (NEW.booking_status IS DISTINCT FROM OLD.booking_status)
EXECUTE FUNCTION webhook_booking_status();

CREATE TRIGGER webhook_accommodation_booking_events_ins
AFTER INSERT ON accommodations
FOR EACH ROW 
EXECUTE FUNCTION webhook_booking_status();

CREATE TRIGGER webhook_accommodation_booking_events_upd
AFTER UPDATE ON accommodations
FOR EACH ROW 
WHEN (NEW.booking_status IS DISTINCT FROM OLD.booking_status)
EXECUTE FUNCTION webhook_booking_status();

-- ===========================
-- WEBHOOK MANAGEMENT FUNCTIONS
-- ===========================

-- Function to test webhook configuration
CREATE OR REPLACE FUNCTION test_webhook(
    p_webhook_name TEXT,
    p_test_payload JSONB DEFAULT '{"test": true}'
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN send_webhook_with_retry(
        p_webhook_name,
        'test.webhook',
        p_test_payload || jsonb_build_object('timestamp', NOW())
    );
END;
$$;

-- Function to get webhook statistics
CREATE OR REPLACE FUNCTION get_webhook_stats(
    p_webhook_name TEXT DEFAULT NULL,
    p_days INTEGER DEFAULT 7
)
RETURNS TABLE (
    webhook_name TEXT,
    total_calls BIGINT,
    successful_calls BIGINT,
    failed_calls BIGINT,
    avg_response_time INTERVAL,
    events JSONB
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT 
        wc.name AS webhook_name,
        COUNT(wl.id) AS total_calls,
        COUNT(wl.id) FILTER (WHERE wl.response_status BETWEEN 200 AND 299) AS successful_calls,
        COUNT(wl.id) FILTER (WHERE wl.response_status IS NULL OR wl.response_status >= 400) AS failed_calls,
        AVG(wl.completed_at - wl.created_at) AS avg_response_time,
        (
          SELECT jsonb_object_agg(ev.event_type, ev.cnt)
          FROM (
            SELECT wl2.event_type, COUNT(*) AS cnt
            FROM webhook_logs wl2
            WHERE wl2.webhook_config_id = wc.id
              AND wl2.created_at > NOW() - INTERVAL '1 day' * p_days
            GROUP BY wl2.event_type
          ) ev
        ) AS events
    FROM webhook_configs wc
    LEFT JOIN webhook_logs wl ON wl.webhook_config_id = wc.id
        AND wl.created_at > NOW() - INTERVAL '1 day' * p_days
    WHERE (p_webhook_name IS NULL OR wc.name = p_webhook_name)
    GROUP BY wc.id, wc.name;
$$;

-- ===========================
-- DEFAULT WEBHOOK CONFIGURATIONS
-- ===========================

-- Insert default webhook configurations
INSERT INTO webhook_configs (name, url, events, headers, is_active) VALUES
    ('trip_events', 
     'https://your-domain.supabase.co/functions/v1/trip-events',
     ARRAY['trip.collaborator.added', 'trip.collaborator.updated', 'trip.collaborator.removed'],
     '{"Authorization": "Bearer YOUR_ANON_KEY"}',
     FALSE),
    
    ('chat_events',
     'https://your-domain.supabase.co/functions/v1/chat-events',
     ARRAY['chat.message.created', 'chat.session.started', 'chat.session.ended'],
     '{"Authorization": "Bearer YOUR_ANON_KEY"}',
     FALSE),
    
    ('booking_events',
     'https://your-domain.supabase.co/functions/v1/booking-events',
     ARRAY['booking.flights.booked', 'booking.accommodations.booked', 'booking.flights.cancelled', 'booking.accommodations.cancelled'],
     '{"Authorization": "Bearer YOUR_ANON_KEY"}',
     FALSE),
    
    ('ai_processing',
     'https://your-domain.supabase.co/functions/v1/ai-processing',
     ARRAY['chat.message.process', 'memory.generate.embedding'],
     '{"Authorization": "Bearer YOUR_ANON_KEY"}',
     FALSE),
    
    ('notification_service',
     'https://your-domain.supabase.co/functions/v1/notifications',
     ARRAY['booking.confirmed', 'trip.reminder', 'collaborator.invited'],
     '{"Authorization": "Bearer YOUR_ANON_KEY"}',
     FALSE),
    
    ('calendar_sync',
     'https://your-domain.supabase.co/functions/v1/calendar-sync',
     ARRAY['calendar.sync.request'],
     '{"Authorization": "Bearer YOUR_ANON_KEY"}',
     FALSE)
ON CONFLICT (name) DO NOTHING;