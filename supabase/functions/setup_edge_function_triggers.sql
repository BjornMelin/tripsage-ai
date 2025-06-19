-- ===================================================================
-- Edge Function Integration Triggers and Functions
-- ===================================================================
-- This file sets up database triggers and functions to integrate
-- with Supabase Edge Functions for automated processing.

-- Function to send webhook notifications to Edge Functions
CREATE OR REPLACE FUNCTION send_edge_function_webhook(
    function_name TEXT,
    payload JSONB
) RETURNS VOID AS $$
DECLARE
    webhook_url TEXT;
    response_status INTEGER;
BEGIN
    -- Build webhook URL
    webhook_url := current_setting('app.supabase_url', true) || '/functions/v1/' || function_name;
    
    -- Log the webhook attempt
    INSERT INTO webhook_logs (
        function_name,
        payload,
        created_at
    ) VALUES (
        function_name,
        payload,
        NOW()
    );
    
    -- In production, this would use pg_net or similar to make HTTP requests
    -- For now, we'll use pg_notify to trigger application-level webhooks
    PERFORM pg_notify('edge_function_webhook', jsonb_build_object(
        'function_name', function_name,
        'payload', payload,
        'timestamp', NOW()
    )::text);
    
EXCEPTION WHEN others THEN
    -- Log webhook errors
    INSERT INTO webhook_logs (
        function_name,
        payload,
        error_message,
        created_at
    ) VALUES (
        function_name,
        payload,
        SQLERRM,
        NOW()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===================================================================
-- TRIP NOTIFICATIONS INTEGRATION
-- ===================================================================

-- Function to handle trip collaboration events
CREATE OR REPLACE FUNCTION handle_trip_collaboration_notification()
RETURNS TRIGGER AS $$
DECLARE
    webhook_payload JSONB;
BEGIN
    -- Build webhook payload
    webhook_payload := jsonb_build_object(
        'type', TG_OP,
        'table', TG_TABLE_NAME,
        'record', CASE 
            WHEN TG_OP = 'DELETE' THEN row_to_json(OLD)::jsonb
            ELSE row_to_json(NEW)::jsonb
        END,
        'old_record', CASE 
            WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD)::jsonb
            ELSE NULL
        END,
        'schema', TG_TABLE_SCHEMA
    );
    
    -- Send to trip-notifications Edge Function
    PERFORM send_edge_function_webhook('trip-notifications', webhook_payload);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create trigger for trip_collaborators
DROP TRIGGER IF EXISTS trip_collaborators_notification_webhook ON trip_collaborators;
CREATE TRIGGER trip_collaborators_notification_webhook
    AFTER INSERT OR UPDATE OR DELETE ON trip_collaborators
    FOR EACH ROW
    EXECUTE FUNCTION handle_trip_collaboration_notification();

-- ===================================================================
-- FILE PROCESSING INTEGRATION
-- ===================================================================

-- Function to handle file upload events
CREATE OR REPLACE FUNCTION handle_file_processing_notification()
RETURNS TRIGGER AS $$
DECLARE
    webhook_payload JSONB;
BEGIN
    -- Only trigger for new file uploads or status changes
    IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND OLD.upload_status != NEW.upload_status) THEN
        
        -- Build webhook payload
        webhook_payload := jsonb_build_object(
            'type', TG_OP,
            'table', TG_TABLE_NAME,
            'record', row_to_json(NEW)::jsonb,
            'old_record', CASE 
                WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD)::jsonb
                ELSE NULL
            END,
            'schema', TG_TABLE_SCHEMA
        );
        
        -- Send to file-processing Edge Function
        PERFORM send_edge_function_webhook('file-processing', webhook_payload);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for file_attachments
DROP TRIGGER IF EXISTS file_attachments_processing_webhook ON file_attachments;
CREATE TRIGGER file_attachments_processing_webhook
    AFTER INSERT OR UPDATE ON file_attachments
    FOR EACH ROW
    EXECUTE FUNCTION handle_file_processing_notification();

-- ===================================================================
-- CACHE INVALIDATION INTEGRATION
-- ===================================================================

-- Function to handle cache invalidation events
CREATE OR REPLACE FUNCTION handle_cache_invalidation_notification()
RETURNS TRIGGER AS $$
DECLARE
    webhook_payload JSONB;
    should_invalidate BOOLEAN := FALSE;
BEGIN
    -- Determine if this change requires cache invalidation
    CASE TG_TABLE_NAME
        WHEN 'trips' THEN
            should_invalidate := TRUE;
        WHEN 'flights' THEN
            should_invalidate := TRUE;
        WHEN 'accommodations' THEN
            should_invalidate := TRUE;
        WHEN 'search_destinations', 'search_flights', 'search_hotels', 'search_activities' THEN
            should_invalidate := TRUE;
        WHEN 'trip_collaborators' THEN
            should_invalidate := TRUE;
        WHEN 'chat_messages', 'chat_sessions' THEN
            should_invalidate := TRUE;
        ELSE
            -- For other tables, only invalidate on significant changes
            should_invalidate := (TG_OP = 'INSERT' OR TG_OP = 'DELETE');
    END CASE;
    
    IF should_invalidate THEN
        -- Build webhook payload
        webhook_payload := jsonb_build_object(
            'type', TG_OP,
            'table', TG_TABLE_NAME,
            'record', CASE 
                WHEN TG_OP = 'DELETE' THEN row_to_json(OLD)::jsonb
                ELSE row_to_json(NEW)::jsonb
            END,
            'old_record', CASE 
                WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD)::jsonb
                ELSE NULL
            END,
            'schema', TG_TABLE_SCHEMA
        );
        
        -- Send to cache-invalidation Edge Function
        PERFORM send_edge_function_webhook('cache-invalidation', webhook_payload);
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create cache invalidation triggers for key tables
DROP TRIGGER IF EXISTS trips_cache_invalidation_webhook ON trips;
CREATE TRIGGER trips_cache_invalidation_webhook
    AFTER INSERT OR UPDATE OR DELETE ON trips
    FOR EACH ROW
    EXECUTE FUNCTION handle_cache_invalidation_notification();

DROP TRIGGER IF EXISTS flights_cache_invalidation_webhook ON flights;
CREATE TRIGGER flights_cache_invalidation_webhook
    AFTER INSERT OR UPDATE OR DELETE ON flights
    FOR EACH ROW
    EXECUTE FUNCTION handle_cache_invalidation_notification();

DROP TRIGGER IF EXISTS accommodations_cache_invalidation_webhook ON accommodations;
CREATE TRIGGER accommodations_cache_invalidation_webhook
    AFTER INSERT OR UPDATE OR DELETE ON accommodations
    FOR EACH ROW
    EXECUTE FUNCTION handle_cache_invalidation_notification();

DROP TRIGGER IF EXISTS search_destinations_cache_invalidation_webhook ON search_destinations;
CREATE TRIGGER search_destinations_cache_invalidation_webhook
    AFTER INSERT OR UPDATE OR DELETE ON search_destinations
    FOR EACH ROW
    EXECUTE FUNCTION handle_cache_invalidation_notification();

DROP TRIGGER IF EXISTS search_flights_cache_invalidation_webhook ON search_flights;
CREATE TRIGGER search_flights_cache_invalidation_webhook
    AFTER INSERT OR UPDATE OR DELETE ON search_flights
    FOR EACH ROW
    EXECUTE FUNCTION handle_cache_invalidation_notification();

DROP TRIGGER IF EXISTS search_hotels_cache_invalidation_webhook ON search_hotels;
CREATE TRIGGER search_hotels_cache_invalidation_webhook
    AFTER INSERT OR UPDATE OR DELETE ON search_hotels
    FOR EACH ROW
    EXECUTE FUNCTION handle_cache_invalidation_notification();

DROP TRIGGER IF EXISTS search_activities_cache_invalidation_webhook ON search_activities;
CREATE TRIGGER search_activities_cache_invalidation_webhook
    AFTER INSERT OR UPDATE OR DELETE ON search_activities
    FOR EACH ROW
    EXECUTE FUNCTION handle_cache_invalidation_notification();

-- ===================================================================
-- WEBHOOK LOGGING TABLE
-- ===================================================================

-- Create table to log webhook attempts (if not exists)
CREATE TABLE IF NOT EXISTS webhook_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    function_name TEXT NOT NULL,
    payload JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for webhook logs
CREATE INDEX IF NOT EXISTS idx_webhook_logs_function_created 
    ON webhook_logs(function_name, created_at DESC);

-- Add cleanup function for webhook logs
CREATE OR REPLACE FUNCTION cleanup_webhook_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete webhook logs older than 30 days
    DELETE FROM webhook_logs 
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ===================================================================
-- NOTIFICATION CHANNELS
-- ===================================================================

-- Function to listen for edge function webhooks in application code
-- Applications can listen to 'edge_function_webhook' channel
COMMENT ON FUNCTION send_edge_function_webhook IS 
'Sends notifications to Edge Functions via pg_notify. Applications should listen to the edge_function_webhook channel.';

-- ===================================================================
-- SECURITY AND PERMISSIONS
-- ===================================================================

-- Grant necessary permissions for webhook functions
GRANT EXECUTE ON FUNCTION send_edge_function_webhook TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_webhook_logs TO authenticated;

-- Allow reading webhook logs for debugging
GRANT SELECT ON webhook_logs TO authenticated;

-- RLS for webhook logs
ALTER TABLE webhook_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can access all webhook logs" ON webhook_logs
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Authenticated users can view webhook logs" ON webhook_logs
    FOR SELECT USING (auth.role() = 'authenticated');

-- ===================================================================
-- USAGE EXAMPLES
-- ===================================================================

/*
-- Example: Manual trigger of trip notification
SELECT send_edge_function_webhook(
    'trip-notifications',
    jsonb_build_object(
        'event_type', 'collaboration_added',
        'trip_id', 123,
        'user_id', 'user-uuid',
        'target_user_id', 'target-uuid',
        'permission_level', 'view'
    )
);

-- Example: Manual trigger of file processing
SELECT send_edge_function_webhook(
    'file-processing',
    jsonb_build_object(
        'file_id', 'file-uuid',
        'operation', 'process_all'
    )
);

-- Example: Manual trigger of cache invalidation
SELECT send_edge_function_webhook(
    'cache-invalidation',
    jsonb_build_object(
        'cache_type', 'all',
        'patterns', jsonb_build_array('trip:*', 'search:*'),
        'reason', 'Manual cleanup'
    )
);

-- Example: Clean up old webhook logs
SELECT cleanup_webhook_logs();

-- Example: View recent webhook activity
SELECT 
    function_name,
    payload->>'type' as operation_type,
    payload->>'table' as table_name,
    error_message,
    created_at
FROM webhook_logs
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
*/