-- Add API Key Usage and Security Monitoring Tables
-- Date: 2025-06-11
-- Description: Add missing tables for API key usage tracking, security monitoring, and session management

-- ===========================
-- API KEY USAGE TRACKING
-- ===========================

-- Create api_key_usage_logs table for audit trail
CREATE TABLE IF NOT EXISTS api_key_usage_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    key_id BIGINT NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    service_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    ip_address INET,
    user_agent TEXT,
    request_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for performance
    CONSTRAINT api_key_usage_logs_operation_check CHECK (operation IN (
        'create', 'update', 'delete', 'validate', 'retrieve', 'rotate', 'use'
    ))
);

-- Create api_key_validation_cache table for caching validation results
CREATE TABLE IF NOT EXISTS api_key_validation_cache (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    key_id BIGINT NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    service_name TEXT NOT NULL,
    is_valid BOOLEAN NOT NULL,
    validation_message TEXT,
    validation_details JSONB DEFAULT '{}',
    validated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '1 hour'),
    
    CONSTRAINT api_key_validation_cache_unique UNIQUE (key_id, service_name)
);

-- ===========================
-- USER SECURITY MONITORING
-- ===========================

-- Create user_sessions table for session management
CREATE TABLE IF NOT EXISTS user_sessions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_token TEXT NOT NULL UNIQUE,
    ip_address INET,
    user_agent TEXT,
    device_info JSONB DEFAULT '{}',
    location_info JSONB DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT user_sessions_dates_check CHECK (expires_at > created_at),
    CONSTRAINT user_sessions_end_check CHECK (ended_at IS NULL OR ended_at >= created_at)
);

-- Create security_events table for security monitoring
CREATE TABLE IF NOT EXISTS security_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    event_category TEXT NOT NULL DEFAULT 'authentication',
    severity TEXT NOT NULL DEFAULT 'info',
    ip_address INET,
    user_agent TEXT,
    details JSONB DEFAULT '{}',
    risk_score INTEGER DEFAULT 0,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT security_events_type_check CHECK (event_type IN (
        'login_success', 'login_failure', 'logout', 'password_reset_request',
        'password_reset_success', 'password_change', 'api_key_created',
        'api_key_deleted', 'suspicious_activity', 'rate_limit_exceeded',
        'oauth_login', 'session_expired', 'invalid_token'
    )),
    CONSTRAINT security_events_category_check CHECK (event_category IN (
        'authentication', 'authorization', 'api_key_management', 'data_access',
        'security_violation', 'system'
    )),
    CONSTRAINT security_events_severity_check CHECK (severity IN (
        'info', 'warning', 'error', 'critical'
    )),
    CONSTRAINT security_events_risk_check CHECK (risk_score >= 0 AND risk_score <= 100)
);

-- ===========================
-- OAUTH PROVIDER METADATA
-- ===========================

-- Create oauth_providers table for OAuth configuration
CREATE TABLE IF NOT EXISTS oauth_providers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider_name TEXT NOT NULL UNIQUE,
    client_id TEXT NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    configuration JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT oauth_providers_name_check CHECK (provider_name IN (
        'google', 'github', 'facebook', 'twitter', 'microsoft', 'apple'
    ))
);

-- Create user_oauth_connections table to track OAuth connections
CREATE TABLE IF NOT EXISTS user_oauth_connections (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider_name TEXT NOT NULL,
    provider_user_id TEXT NOT NULL,
    email TEXT,
    display_name TEXT,
    avatar_url TEXT,
    access_token_hash TEXT,
    refresh_token_hash TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    profile_data JSONB DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT user_oauth_connections_unique UNIQUE (user_id, provider_name),
    CONSTRAINT user_oauth_connections_provider_unique UNIQUE (provider_name, provider_user_id)
);

-- ===========================
-- INDEXES FOR PERFORMANCE
-- ===========================

-- API Key Usage Logs indexes
CREATE INDEX IF NOT EXISTS idx_api_key_usage_logs_key_id ON api_key_usage_logs(key_id);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_logs_user_id ON api_key_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_logs_created_at ON api_key_usage_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_logs_service ON api_key_usage_logs(service_name);

-- Validation Cache indexes
CREATE INDEX IF NOT EXISTS idx_api_key_validation_cache_expires ON api_key_validation_cache(expires_at);

-- User Sessions indexes
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_sessions_last_activity ON user_sessions(last_activity_at DESC);

-- Security Events indexes
CREATE INDEX IF NOT EXISTS idx_security_events_user_id ON security_events(user_id);
CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_created_at ON security_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events(severity);
CREATE INDEX IF NOT EXISTS idx_security_events_risk_score ON security_events(risk_score DESC);

-- OAuth Connections indexes
CREATE INDEX IF NOT EXISTS idx_user_oauth_connections_user_id ON user_oauth_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_user_oauth_connections_provider ON user_oauth_connections(provider_name);
CREATE INDEX IF NOT EXISTS idx_user_oauth_connections_active ON user_oauth_connections(is_active) WHERE is_active = TRUE;

-- ===========================
-- COMMENTS FOR DOCUMENTATION
-- ===========================

-- Table comments
COMMENT ON TABLE api_key_usage_logs IS 'Audit trail for all API key operations and usage';
COMMENT ON TABLE api_key_validation_cache IS 'Cache validation results to avoid repeated API calls';
COMMENT ON TABLE user_sessions IS 'Track active user sessions for security and analytics';
COMMENT ON TABLE security_events IS 'Log security-related events for monitoring and analysis';
COMMENT ON TABLE oauth_providers IS 'Configuration for OAuth providers';
COMMENT ON TABLE user_oauth_connections IS 'Track user connections to OAuth providers';

-- Column comments for key tables
COMMENT ON COLUMN api_key_usage_logs.operation IS 'Type of operation performed on the API key';
COMMENT ON COLUMN security_events.risk_score IS 'Risk score from 0-100, higher values indicate more suspicious activity';
COMMENT ON COLUMN user_sessions.device_info IS 'JSON containing device fingerprint and capabilities';
COMMENT ON COLUMN user_oauth_connections.profile_data IS 'JSON containing additional profile data from OAuth provider';