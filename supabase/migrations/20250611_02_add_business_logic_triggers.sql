-- Migration: Add Business Logic and Automation Triggers
-- Description: Implements collaboration events, cache invalidation, and business logic triggers
-- Dependencies: Previous migrations with base schema

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
    SELECT name INTO v_trip_name FROM trips WHERE id = COALESCE(NEW.trip_id, OLD.trip_id);
    
    -- Get user emails for notification context
    SELECT email INTO v_added_by_email FROM users WHERE id = COALESCE(NEW.added_by, OLD.added_by);
    SELECT email INTO v_user_email FROM users WHERE id = COALESCE(NEW.user_id, OLD.user_id);
    
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
    
    RETURN COALESCE(NEW, OLD);
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
    -- Run comprehensive maintenance
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
-- CREATE TRIGGERS
-- ===========================

-- Add missing updated_at triggers
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

CREATE TRIGGER update_trip_notes_updated_at 
    BEFORE UPDATE ON trip_notes 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_saved_options_updated_at 
    BEFORE UPDATE ON saved_options 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trip_comparisons_updated_at 
    BEFORE UPDATE ON trip_comparisons 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_price_history_updated_at 
    BEFORE UPDATE ON price_history 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Collaboration event triggers
CREATE TRIGGER notify_trip_collaboration_changes
    AFTER INSERT OR UPDATE OR DELETE ON trip_collaborators
    FOR EACH ROW
    EXECUTE FUNCTION notify_collaboration_change();

CREATE TRIGGER validate_collaboration_permissions_trigger
    BEFORE INSERT OR UPDATE ON trip_collaborators
    FOR EACH ROW
    EXECUTE FUNCTION validate_collaboration_permissions();

CREATE TRIGGER audit_trip_collaboration_changes
    AFTER UPDATE ON trip_collaborators
    FOR EACH ROW
    EXECUTE FUNCTION audit_collaboration_changes();

-- Cache invalidation triggers
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

-- Business logic triggers
CREATE TRIGGER auto_expire_inactive_sessions
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    WHEN (NEW.updated_at IS DISTINCT FROM OLD.updated_at)
    EXECUTE FUNCTION auto_expire_chat_session();

CREATE TRIGGER cleanup_message_attachments
    AFTER DELETE ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_orphaned_attachments();

CREATE TRIGGER update_trip_status_from_flight_bookings
    AFTER INSERT OR UPDATE ON flights
    FOR EACH ROW
    WHEN (NEW.booking_status IS DISTINCT FROM OLD.booking_status OR TG_OP = 'INSERT')
    EXECUTE FUNCTION update_trip_status_from_bookings();

CREATE TRIGGER update_trip_status_from_accommodation_bookings
    AFTER INSERT OR UPDATE ON accommodations
    FOR EACH ROW
    WHEN (NEW.booking_status IS DISTINCT FROM OLD.booking_status OR TG_OP = 'INSERT')
    EXECUTE FUNCTION update_trip_status_from_bookings();

-- ===========================
-- PG_CRON SCHEDULED JOBS SETUP
-- ===========================

-- Note: These need to be run by a superuser after enabling pg_cron extension
-- Uncomment and run these if pg_cron is available:

/*
-- Enable pg_cron extension (run as superuser)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule daily cleanup (runs at 2 AM UTC)
SELECT cron.schedule('daily-cleanup', '0 2 * * *', 'SELECT daily_cleanup_job();');

-- Schedule weekly maintenance (runs Sunday at 3 AM UTC)
SELECT cron.schedule('weekly-maintenance', '0 3 * * 0', 'SELECT weekly_maintenance_job();');

-- Schedule monthly deep cleanup (runs on the 1st at 4 AM UTC)
SELECT cron.schedule('monthly-cleanup', '0 4 1 * *', 'SELECT monthly_cleanup_job();');

-- Schedule search cache cleanup (runs every 6 hours)
SELECT cron.schedule('search-cache-cleanup', '0 */6 * * *', 'SELECT cleanup_expired_search_cache();');

-- Schedule session expiration check (runs every hour)
SELECT cron.schedule('expire-sessions', '0 * * * *', 'SELECT expire_inactive_sessions(24);');
*/