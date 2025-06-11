-- Migration: Add trip collaborators table
-- Description: Creates the trip_collaborators table for sharing trips between users
-- Date: 2025-06-11

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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_trip_collaborators_trip_id ON trip_collaborators(trip_id);
CREATE INDEX IF NOT EXISTS idx_trip_collaborators_user_id ON trip_collaborators(user_id);
CREATE INDEX IF NOT EXISTS idx_trip_collaborators_added_by ON trip_collaborators(added_by);

-- Add RLS (Row Level Security) policies
ALTER TABLE trip_collaborators ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view collaborations they are part of
CREATE POLICY trip_collaborators_select_policy ON trip_collaborators
    FOR SELECT
    USING (
        user_id = auth.uid() OR 
        added_by = auth.uid() OR
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
        )
    );

-- Policy: Trip owners can manage collaborators
CREATE POLICY trip_collaborators_insert_policy ON trip_collaborators
    FOR INSERT
    WITH CHECK (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
        )
    );

-- Policy: Trip owners can update collaborators
CREATE POLICY trip_collaborators_update_policy ON trip_collaborators
    FOR UPDATE
    USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
        )
    );

-- Policy: Trip owners can delete collaborators
CREATE POLICY trip_collaborators_delete_policy ON trip_collaborators
    FOR DELETE
    USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id = auth.uid()
        )
    );