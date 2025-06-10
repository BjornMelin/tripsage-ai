-- Migration: Add Authentication Fields to Users
-- Description: Adds password_hash, is_admin, and is_disabled fields to the users table
-- Created: 2025-05-10

-- Add columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS password_hash TEXT,
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_disabled BOOLEAN DEFAULT FALSE;

-- Add indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_users_is_admin ON users (is_admin);
CREATE INDEX IF NOT EXISTS idx_users_is_disabled ON users (is_disabled);

-- Add comments for the new columns
COMMENT ON COLUMN users.password_hash IS 'Hashed password for user authentication';
COMMENT ON COLUMN users.is_admin IS 'Flag indicating whether the user has admin privileges';
COMMENT ON COLUMN users.is_disabled IS 'Flag indicating whether the user account is disabled';

-- Create a function to verify user authentication
CREATE OR REPLACE FUNCTION check_user_auth(
    p_email TEXT,
    p_password_hash TEXT
) RETURNS TABLE (
    id BIGINT,
    email TEXT,
    name TEXT,
    is_admin BOOLEAN,
    is_disabled BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT u.id, u.email, u.name, u.is_admin, u.is_disabled
    FROM users u
    WHERE u.email = p_email
    AND u.password_hash = p_password_hash
    AND u.is_disabled = FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;