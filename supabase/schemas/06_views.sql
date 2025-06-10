-- Database Views Schema
-- Description: Commonly used database views for efficient querying
-- Dependencies: 01_tables.sql (all table definitions)

-- ===========================
-- CHAT SYSTEM VIEWS
-- ===========================

-- Create view for active chat sessions with statistics
CREATE OR REPLACE VIEW active_chat_sessions AS
SELECT 
    cs.id,
    cs.user_id,
    cs.trip_id,
    cs.created_at,
    cs.updated_at,
    cs.metadata,
    COUNT(cm.id) as message_count,
    MAX(cm.created_at) as last_message_at
FROM chat_sessions cs
LEFT JOIN chat_messages cm ON cs.id = cm.session_id
WHERE cs.ended_at IS NULL
GROUP BY cs.id, cs.user_id, cs.trip_id, cs.created_at, cs.updated_at, cs.metadata;

-- ===========================
-- TRIP MANAGEMENT VIEWS
-- ===========================

-- Create view for trip summaries with related data counts and costs
CREATE OR REPLACE VIEW trip_summaries AS
SELECT 
    t.id,
    t.user_id,
    t.name,
    t.destination,
    t.start_date,
    t.end_date,
    t.budget,
    t.status,
    COUNT(DISTINCT f.id) as flight_count,
    COUNT(DISTINCT a.id) as accommodation_count,
    COUNT(DISTINCT ii.id) as itinerary_item_count,
    SUM(f.price) as total_flight_cost,
    SUM(a.total_price) as total_accommodation_cost
FROM trips t
LEFT JOIN flights f ON t.id = f.trip_id
LEFT JOIN accommodations a ON t.id = a.trip_id  
LEFT JOIN itinerary_items ii ON t.id = ii.trip_id
GROUP BY t.id, t.user_id, t.name, t.destination, t.start_date, t.end_date, t.budget, t.status;

-- Create view for user trip statistics
CREATE OR REPLACE VIEW user_trip_stats AS
SELECT 
    user_id,
    COUNT(*) as total_trips,
    COUNT(CASE WHEN status = 'planning' THEN 1 END) as planning_trips,
    COUNT(CASE WHEN status = 'booked' THEN 1 END) as booked_trips,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_trips,
    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_trips,
    AVG(budget) as average_budget,
    SUM(budget) as total_budget,
    MIN(created_at) as first_trip_created,
    MAX(created_at) as last_trip_created
FROM trips
GROUP BY user_id;

-- ===========================
-- BOOKING STATUS VIEWS
-- ===========================

-- Create view for upcoming bookings (flights and accommodations)
CREATE OR REPLACE VIEW upcoming_bookings AS
SELECT 
    'flight' as booking_type,
    f.id::TEXT as booking_id,
    t.user_id,
    t.id as trip_id,
    t.name as trip_name,
    f.origin || ' → ' || f.destination as description,
    f.departure_date as booking_date,
    f.price,
    f.currency,
    f.booking_status
FROM flights f
JOIN trips t ON f.trip_id = t.id
WHERE f.departure_date >= CURRENT_DATE
    AND f.booking_status IN ('reserved', 'booked')

UNION ALL

SELECT 
    'accommodation' as booking_type,
    a.id::TEXT as booking_id,
    t.user_id,
    t.id as trip_id,
    t.name as trip_name,
    a.name as description,
    a.check_in_date as booking_date,
    a.total_price as price,
    a.currency,
    a.booking_status
FROM accommodations a
JOIN trips t ON a.trip_id = t.id
WHERE a.check_in_date >= CURRENT_DATE
    AND a.booking_status IN ('reserved', 'booked')

ORDER BY booking_date ASC;

-- ===========================
-- API USAGE VIEWS
-- ===========================

-- Create view for active API keys by service
CREATE OR REPLACE VIEW active_api_keys_by_service AS
SELECT 
    service_name,
    COUNT(*) as total_keys,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_keys,
    COUNT(CASE WHEN last_used_at IS NOT NULL THEN 1 END) as used_keys,
    MAX(last_used_at) as last_usage,
    COUNT(CASE WHEN expires_at IS NOT NULL AND expires_at < NOW() THEN 1 END) as expired_keys
FROM api_keys
GROUP BY service_name
ORDER BY total_keys DESC;

-- Create view for user API key status
CREATE OR REPLACE VIEW user_api_key_status AS
SELECT 
    user_id,
    COUNT(*) as total_keys,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_keys,
    array_agg(DISTINCT service_name) as services,
    MIN(created_at) as first_key_added,
    MAX(last_used_at) as last_api_usage
FROM api_keys
GROUP BY user_id;

-- ===========================
-- MEMORY SYSTEM VIEWS
-- ===========================

-- Create view for memory statistics by user
CREATE OR REPLACE VIEW user_memory_stats AS
SELECT 
    user_id,
    COUNT(*) as total_memories,
    COUNT(CASE WHEN memory_type = 'user_preference' THEN 1 END) as preference_memories,
    COUNT(CASE WHEN memory_type = 'trip_history' THEN 1 END) as trip_history_memories,
    COUNT(CASE WHEN memory_type = 'search_pattern' THEN 1 END) as search_pattern_memories,
    COUNT(CASE WHEN memory_type = 'conversation_context' THEN 1 END) as conversation_memories,
    MIN(created_at) as first_memory,
    MAX(updated_at) as last_memory_update
FROM memories
GROUP BY user_id;

-- ===========================
-- VIEW COMMENTS
-- ===========================

COMMENT ON VIEW active_chat_sessions IS 'Active chat sessions with message count and last activity';
COMMENT ON VIEW trip_summaries IS 'Trip overview with associated bookings count and total costs';
COMMENT ON VIEW user_trip_stats IS 'User-level trip statistics and spending patterns';
COMMENT ON VIEW upcoming_bookings IS 'All upcoming confirmed bookings (flights and accommodations)';
COMMENT ON VIEW active_api_keys_by_service IS 'API key usage statistics by service type';
COMMENT ON VIEW user_api_key_status IS 'User-level API key management overview';
COMMENT ON VIEW user_memory_stats IS 'User memory system usage and categorization statistics';