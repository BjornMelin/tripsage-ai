-- Schema Alignment Fixes Migration
-- Description: Aligns database schema with frontend and backend expectations
-- Created: 2025-06-11
-- Version: 1.0
-- Purpose: Fix ID types, field names, and missing columns across all layers

-- ===========================
-- PHASE 1: ADD MISSING COLUMNS
-- ===========================

-- Add missing columns to trips table
ALTER TABLE trips 
ADD COLUMN IF NOT EXISTS visibility TEXT DEFAULT 'private',
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}';

-- Add constraints for new columns
ALTER TABLE trips 
ADD CONSTRAINT trips_visibility_check CHECK (visibility IN ('private', 'shared', 'public'));

-- Create index for tags array search
CREATE INDEX IF NOT EXISTS idx_trips_tags ON trips USING GIN (tags);

-- Create index for JSONB preferences
CREATE INDEX IF NOT EXISTS idx_trips_preferences ON trips USING GIN (preferences);

-- ===========================
-- PHASE 2: PREPARE FOR ID MIGRATION
-- ===========================

-- Add new UUID columns (temporary, for migration)
ALTER TABLE trips ADD COLUMN IF NOT EXISTS uuid_id UUID DEFAULT uuid_generate_v4();
ALTER TABLE flights ADD COLUMN IF NOT EXISTS uuid_id UUID DEFAULT uuid_generate_v4();
ALTER TABLE flights ADD COLUMN IF NOT EXISTS trip_uuid UUID;
ALTER TABLE accommodations ADD COLUMN IF NOT EXISTS uuid_id UUID DEFAULT uuid_generate_v4();
ALTER TABLE accommodations ADD COLUMN IF NOT EXISTS trip_uuid UUID;
ALTER TABLE transportation ADD COLUMN IF NOT EXISTS uuid_id UUID DEFAULT uuid_generate_v4();
ALTER TABLE transportation ADD COLUMN IF NOT EXISTS trip_uuid UUID;
ALTER TABLE itinerary_items ADD COLUMN IF NOT EXISTS uuid_id UUID DEFAULT uuid_generate_v4();
ALTER TABLE itinerary_items ADD COLUMN IF NOT EXISTS trip_uuid UUID;
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS trip_uuid UUID;
ALTER TABLE trip_collaborators ADD COLUMN IF NOT EXISTS uuid_id UUID DEFAULT uuid_generate_v4();
ALTER TABLE trip_collaborators ADD COLUMN IF NOT EXISTS trip_uuid UUID;

-- Create unique indexes for UUID columns
CREATE UNIQUE INDEX IF NOT EXISTS idx_trips_uuid ON trips(uuid_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_flights_uuid ON flights(uuid_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_accommodations_uuid ON accommodations(uuid_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_transportation_uuid ON transportation(uuid_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_itinerary_items_uuid ON itinerary_items(uuid_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_trip_collaborators_uuid ON trip_collaborators(uuid_id);

-- ===========================
-- PHASE 3: FIELD NAME ALIGNMENT
-- ===========================

-- Add 'title' column as alias for 'name' (for API compatibility)
-- We'll use a generated column to maintain both field names
ALTER TABLE trips 
ADD COLUMN IF NOT EXISTS title TEXT GENERATED ALWAYS AS (name) STORED;

-- Create index on title for search performance
CREATE INDEX IF NOT EXISTS idx_trips_title ON trips(title);

-- ===========================
-- PHASE 4: MEM0 INTEGRATION TABLES
-- ===========================

-- Create mem0_collections table for Mem0 compatibility
CREATE TABLE IF NOT EXISTS mem0_collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create mem0_memories table (extension of our memories table)
CREATE TABLE IF NOT EXISTS mem0_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID NOT NULL REFERENCES mem0_collections(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for Mem0 tables
CREATE INDEX IF NOT EXISTS idx_mem0_memories_collection ON mem0_memories(collection_id);
CREATE INDEX IF NOT EXISTS idx_mem0_memories_user ON mem0_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_mem0_memories_embedding ON mem0_memories USING ivfflat (embedding vector_cosine_ops);

-- ===========================
-- PHASE 5: MIGRATION FUNCTIONS
-- ===========================

-- Function to populate UUID references
CREATE OR REPLACE FUNCTION populate_uuid_references() RETURNS void AS $$
BEGIN
    -- Update trip references in related tables
    UPDATE flights f SET trip_uuid = t.uuid_id 
    FROM trips t WHERE f.trip_id = t.id;
    
    UPDATE accommodations a SET trip_uuid = t.uuid_id 
    FROM trips t WHERE a.trip_id = t.id;
    
    UPDATE transportation tr SET trip_uuid = t.uuid_id 
    FROM trips t WHERE tr.trip_id = t.id;
    
    UPDATE itinerary_items i SET trip_uuid = t.uuid_id 
    FROM trips t WHERE i.trip_id = t.id;
    
    UPDATE chat_sessions c SET trip_uuid = t.uuid_id 
    FROM trips t WHERE c.trip_id = t.id;
    
    UPDATE trip_collaborators tc SET trip_uuid = t.uuid_id 
    FROM trips t WHERE tc.trip_id = t.id;
END;
$$ LANGUAGE plpgsql;

-- Execute the reference population
SELECT populate_uuid_references();

-- ===========================
-- PHASE 6: DATA TYPE ADAPTERS
-- ===========================

-- Create adapter views for backward compatibility during transition
CREATE OR REPLACE VIEW trips_compatible AS
SELECT 
    id AS id_bigint,
    uuid_id AS id,
    user_id,
    name,
    title,
    start_date,
    end_date,
    destination,
    budget,
    travelers,
    status,
    trip_type,
    flexibility,
    notes,
    search_metadata,
    visibility,
    tags,
    preferences,
    created_at,
    updated_at
FROM trips;

-- Create function to handle ID type conversion in API layer
CREATE OR REPLACE FUNCTION get_trip_by_any_id(trip_identifier TEXT) 
RETURNS SETOF trips AS $$
BEGIN
    -- Try to parse as UUID first
    BEGIN
        RETURN QUERY SELECT * FROM trips WHERE uuid_id = trip_identifier::UUID;
        IF FOUND THEN RETURN; END IF;
    EXCEPTION WHEN invalid_text_representation THEN
        -- Not a valid UUID, try as BIGINT
        NULL;
    END;
    
    -- Try as BIGINT ID
    BEGIN
        RETURN QUERY SELECT * FROM trips WHERE id = trip_identifier::BIGINT;
    EXCEPTION WHEN invalid_text_representation THEN
        -- Not a valid BIGINT either
        RETURN;
    END;
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- PHASE 7: RLS POLICIES UPDATE
-- ===========================

-- Update RLS policies to handle new fields
DROP POLICY IF EXISTS trips_visibility_policy ON trips;
CREATE POLICY trips_visibility_policy ON trips FOR SELECT
    USING (
        -- Owner can always see
        auth.uid() = user_id 
        -- Public trips visible to all
        OR visibility = 'public'
        -- Shared trips visible to collaborators
        OR (visibility = 'shared' AND EXISTS (
            SELECT 1 FROM trip_collaborators 
            WHERE trip_collaborators.trip_id = trips.id 
            AND trip_collaborators.user_id = auth.uid()
        ))
    );

-- ===========================
-- PHASE 8: VALIDATION
-- ===========================

-- Validation queries
DO $$
BEGIN
    -- Check if all new columns exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trips' AND column_name = 'visibility') THEN
        RAISE EXCEPTION 'visibility column not created';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trips' AND column_name = 'tags') THEN
        RAISE EXCEPTION 'tags column not created';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trips' AND column_name = 'preferences') THEN
        RAISE EXCEPTION 'preferences column not created';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trips' AND column_name = 'title') THEN
        RAISE EXCEPTION 'title column not created';
    END IF;
    
    RAISE NOTICE 'Schema alignment migration completed successfully!';
END $$;

-- ===========================
-- MIGRATION NOTES
-- ===========================

COMMENT ON MIGRATION '20250611_02_schema_alignment_fixes' IS 
'Aligns database schema with frontend and backend expectations:
- Adds missing columns (visibility, tags, preferences)
- Prepares for UUID migration while maintaining BIGINT compatibility
- Adds title as generated column for API compatibility
- Creates Mem0 integration tables
- Provides adapter functions for smooth transition';