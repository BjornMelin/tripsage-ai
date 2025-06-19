-- Schema Alignment Migration
-- Description: Comprehensive migration to align trip schema across frontend, backend, and database
-- Dependencies: Previous migration files
-- Author: Schema Alignment Sub-Agent
-- Date: 2025-01-11

-- ===========================
-- PHASE 1: TRIP TABLE ENHANCEMENTS
-- ===========================

BEGIN;

-- Add UUID support for future ID standardization
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Add missing fields to trips table
ALTER TABLE trips 
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS visibility TEXT DEFAULT 'private',
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS preferences_extended JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS uuid_id UUID DEFAULT uuid_generate_v4();

-- Add budget enhancement fields
ALTER TABLE trips 
ADD COLUMN IF NOT EXISTS budget_breakdown JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'USD',
ADD COLUMN IF NOT EXISTS spent_amount NUMERIC DEFAULT 0;

-- Rename name to title for consistency (with backup)
DO $$ 
BEGIN
    -- Check if 'name' column exists and 'title' doesn't
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'name'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'title'
    ) THEN
        ALTER TABLE trips RENAME COLUMN name TO title;
    END IF;
END $$;

-- Add constraints for new fields
ALTER TABLE trips 
ADD CONSTRAINT IF NOT EXISTS trips_visibility_check 
CHECK (visibility IN ('private', 'shared', 'public'));

ALTER TABLE trips 
ADD CONSTRAINT IF NOT EXISTS trips_spent_amount_check 
CHECK (spent_amount >= 0);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_trips_uuid_id ON trips(uuid_id);
CREATE INDEX IF NOT EXISTS idx_trips_visibility ON trips(visibility);
CREATE INDEX IF NOT EXISTS idx_trips_tags ON trips USING GIN(tags);

-- ===========================
-- PHASE 2: DATA MIGRATION
-- ===========================

-- Migrate existing search_metadata to preferences_extended
UPDATE trips 
SET preferences_extended = COALESCE(
    jsonb_build_object(
        'budget', jsonb_build_object(
            'total', budget,
            'currency', COALESCE(currency, 'USD'),
            'spent', COALESCE(spent_amount, 0),
            'breakdown', COALESCE(budget_breakdown, '{}'::jsonb)
        ),
        'flexibility', COALESCE(flexibility, '{}'::jsonb),
        'search_metadata', COALESCE(search_metadata, '{}'::jsonb)
    ),
    '{}'::jsonb
)
WHERE preferences_extended = '{}'::jsonb OR preferences_extended IS NULL;

-- Set default currency for existing trips
UPDATE trips 
SET currency = 'USD' 
WHERE currency IS NULL;

-- Set default visibility for existing trips
UPDATE trips 
SET visibility = 'private' 
WHERE visibility IS NULL;

-- ===========================
-- PHASE 3: ENHANCED COLLABORATION SUPPORT
-- ===========================

-- Update trip_collaborators table to support enhanced permissions
ALTER TABLE trip_collaborators 
ADD COLUMN IF NOT EXISTS role_permissions JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS invitation_status TEXT DEFAULT 'active',
ADD COLUMN IF NOT EXISTS invited_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMP WITH TIME ZONE;

-- Add constraints for collaboration enhancements
ALTER TABLE trip_collaborators 
ADD CONSTRAINT IF NOT EXISTS trip_collaborators_invitation_status_check 
CHECK (invitation_status IN ('pending', 'active', 'declined', 'revoked'));

-- Create index for invitation queries
CREATE INDEX IF NOT EXISTS idx_trip_collaborators_invitation_status 
ON trip_collaborators(invitation_status);

-- ===========================
-- PHASE 4: MEMORY SYSTEM COMPATIBILITY
-- ===========================

-- Ensure memories table is compatible with enhanced trip preferences
-- Add trip context indexing for better memory retrieval
CREATE INDEX IF NOT EXISTS idx_memories_trip_context 
ON memories USING GIN(metadata) 
WHERE metadata ? 'trip_id';

-- Add session memories indexing for trip-specific conversations
CREATE INDEX IF NOT EXISTS idx_session_memories_trip_context 
ON session_memories USING GIN(metadata) 
WHERE metadata ? 'trip_id';

-- ===========================
-- PHASE 5: VIEW CREATION FOR COMPATIBILITY
-- ===========================

-- Create view for backward compatibility with legacy 'name' field
CREATE OR REPLACE VIEW trips_legacy AS 
SELECT 
    id,
    user_id,
    title AS name,  -- Map title back to name for legacy support
    title,
    description,
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
    preferences_extended AS preferences,
    budget_breakdown,
    currency,
    spent_amount,
    uuid_id,
    created_at,
    updated_at
FROM trips;

-- Create enhanced trip view with computed fields
CREATE OR REPLACE VIEW trips_enhanced AS 
SELECT 
    t.*,
    uuid_id AS trip_uuid,
    (end_date - start_date) AS duration_days,
    CASE 
        WHEN budget > 0 THEN spent_amount / budget * 100 
        ELSE 0 
    END AS budget_utilization_percentage,
    COALESCE(array_length(tags, 1), 0) AS tag_count,
    CASE 
        WHEN visibility = 'shared' THEN 
            (SELECT COUNT(*) FROM trip_collaborators tc WHERE tc.trip_id = t.id)
        ELSE 0 
    END AS collaborator_count
FROM trips t;

-- ===========================
-- PHASE 6: FUNCTIONS FOR SCHEMA COMPATIBILITY
-- ===========================

-- Function to get trip by either BIGINT ID or UUID
CREATE OR REPLACE FUNCTION get_trip_by_any_id(trip_identifier TEXT)
RETURNS trips AS $$
DECLARE
    trip_record trips;
BEGIN
    -- Try to parse as UUID first
    BEGIN
        SELECT * INTO trip_record FROM trips WHERE uuid_id = trip_identifier::UUID;
        IF FOUND THEN
            RETURN trip_record;
        END IF;
    EXCEPTION WHEN invalid_text_representation THEN
        -- Not a valid UUID, continue to BIGINT check
        NULL;
    END;
    
    -- Try to parse as BIGINT
    BEGIN
        SELECT * INTO trip_record FROM trips WHERE id = trip_identifier::BIGINT;
        IF FOUND THEN
            RETURN trip_record;
        END IF;
    EXCEPTION WHEN invalid_text_representation THEN
        -- Not a valid BIGINT either
        NULL;
    END;
    
    -- No match found
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Function to create enhanced trip preferences
CREATE OR REPLACE FUNCTION update_trip_preferences(
    trip_id BIGINT,
    new_preferences JSONB
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE trips 
    SET 
        preferences_extended = preferences_extended || new_preferences,
        updated_at = NOW()
    WHERE id = trip_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- PHASE 7: VALIDATION AND CLEANUP
-- ===========================

-- Validate data integrity
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    -- Check for trips without required fields
    SELECT COUNT(*) INTO invalid_count 
    FROM trips 
    WHERE title IS NULL OR title = '';
    
    IF invalid_count > 0 THEN
        RAISE NOTICE 'Found % trips with invalid titles', invalid_count;
    END IF;
    
    -- Check for invalid visibility values
    SELECT COUNT(*) INTO invalid_count 
    FROM trips 
    WHERE visibility NOT IN ('private', 'shared', 'public');
    
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Found % trips with invalid visibility values', invalid_count;
    END IF;
    
    RAISE NOTICE 'Schema alignment migration completed successfully';
END $$;

COMMIT;

-- ===========================
-- PHASE 8: GRANTS AND PERMISSIONS
-- ===========================

-- Ensure proper RLS policies are maintained
-- (Existing RLS policies from 05_policies.sql should still apply)

-- Grant necessary permissions for new views
GRANT SELECT ON trips_legacy TO authenticated;
GRANT SELECT ON trips_enhanced TO authenticated;

-- Update existing RLS policies to include new fields
CREATE POLICY IF NOT EXISTS "trips_enhanced_access" ON trips
    FOR ALL USING (auth.uid() = user_id OR 
                   id IN (SELECT trip_id FROM trip_collaborators WHERE user_id = auth.uid()));

-- Performance optimization: Update table statistics
ANALYZE trips;
ANALYZE trip_collaborators;
ANALYZE memories;
ANALYZE session_memories;