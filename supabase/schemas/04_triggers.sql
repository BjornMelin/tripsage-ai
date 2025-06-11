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

CREATE TRIGGER update_api_keys_updated_at 
    BEFORE UPDATE ON api_keys 
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