-- Migration: Add API Keys Table
-- Description: Creates the api_keys table for BYOK (Bring Your Own Key) functionality
-- Created: 2025-01-22

-- Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    service TEXT NOT NULL,
    encrypted_key TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    
    -- Constraints
    CONSTRAINT api_keys_name_length CHECK (length(name) >= 1 AND length(name) <= 255),
    CONSTRAINT api_keys_service_length CHECK (length(service) >= 1 AND length(service) <= 255),
    CONSTRAINT api_keys_service_format CHECK (service ~ '^[a-z0-9_-]+$'),
    CONSTRAINT api_keys_user_service_unique UNIQUE (user_id, service, name)
);

COMMENT ON TABLE api_keys IS 'User API keys for external services (BYOK - Bring Your Own Key)';
COMMENT ON COLUMN api_keys.id IS 'Unique identifier for the API key (UUID)';
COMMENT ON COLUMN api_keys.user_id IS 'Reference to the user who owns this API key';
COMMENT ON COLUMN api_keys.name IS 'User-friendly name for the API key';
COMMENT ON COLUMN api_keys.service IS 'Service name this key is for (e.g., openai, google_maps, weather)';
COMMENT ON COLUMN api_keys.encrypted_key IS 'Encrypted API key value using envelope encryption';
COMMENT ON COLUMN api_keys.description IS 'Optional description of the API key';
COMMENT ON COLUMN api_keys.created_at IS 'Timestamp when the API key was created';
COMMENT ON COLUMN api_keys.updated_at IS 'Timestamp when the API key was last updated';
COMMENT ON COLUMN api_keys.expires_at IS 'Optional expiration timestamp for the API key';
COMMENT ON COLUMN api_keys.last_used IS 'Timestamp when the API key was last used';
COMMENT ON COLUMN api_keys.is_active IS 'Whether the API key is active and can be used';

-- Create trigger for api_keys table to update updated_at
CREATE TRIGGER update_api_keys_updated_at
BEFORE UPDATE ON api_keys
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_service ON api_keys(service);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_service ON api_keys(user_id, service);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);