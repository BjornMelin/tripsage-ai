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

CREATE TRIGGER webhook_flight_booking_events
AFTER INSERT OR UPDATE ON flights
FOR EACH ROW 
WHEN (NEW.booking_status IS DISTINCT FROM OLD.booking_status)
EXECUTE FUNCTION webhook_booking_status();

CREATE TRIGGER webhook_accommodation_booking_events
AFTER INSERT OR UPDATE ON accommodations
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
        wc.name,
        COUNT(wl.id) AS total_calls,
        COUNT(wl.id) FILTER (WHERE wl.response_status BETWEEN 200 AND 299) AS successful_calls,
        COUNT(wl.id) FILTER (WHERE wl.response_status IS NULL OR wl.response_status >= 400) AS failed_calls,
        AVG(wl.completed_at - wl.created_at) AS avg_response_time,
        jsonb_object_agg(
            wl.event_type, 
            COUNT(wl.id)
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