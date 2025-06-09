-- Seed Data for TripSage Development
-- Description: Initial development data for testing and demonstration
-- Dependencies: Complete schema from consolidated migration

-- Note: This seed data uses placeholder user IDs that should be replaced
-- with real auth.users UUIDs in a production environment

-- ===========================
-- DEVELOPMENT USER SETUP
-- ===========================

-- Insert development users into auth.users (Supabase handles this in production)
-- This is for local development only - production users come from Supabase Auth
INSERT INTO auth.users (
    id,
    email,
    email_confirmed_at,
    created_at,
    updated_at,
    raw_app_meta_data,
    raw_user_meta_data
) VALUES 
(
    '00000000-0000-0000-0000-000000000001'::UUID,
    'demo@tripsage.ai',
    NOW(),
    NOW(),
    NOW(),
    '{"provider": "email", "providers": ["email"]}',
    '{"name": "Demo User"}'
) ON CONFLICT (id) DO NOTHING;

-- ===========================
-- SAMPLE TRIP DATA
-- ===========================

-- Insert sample trips for development and testing
INSERT INTO trips (
    user_id,
    name,
    start_date,
    end_date,
    destination,
    budget,
    travelers,
    status,
    trip_type,
    flexibility,
    notes,
    search_metadata
) VALUES 
(
    '00000000-0000-0000-0000-000000000001'::UUID,
    'Summer Vacation in Japan',
    '2025-07-15',
    '2025-07-30',
    'Tokyo, Japan',
    5000.00,
    2,
    'planning',
    'leisure',
    '{"date_flexibility": 3, "budget_flexibility": 0.1}',
    ARRAY['Visit traditional temples', 'Try authentic sushi', 'Experience cherry blossom season'],
    '{"preferred_flight_class": "economy", "accommodation_type": "hotel", "activities": ["cultural", "food", "nature"]}'
),
(
    '00000000-0000-0000-0000-000000000001'::UUID,
    'Business Trip to New York',
    '2025-08-10',
    '2025-08-15',
    'New York, USA',
    3000.00,
    1,
    'booked',
    'business',
    '{"date_flexibility": 0, "budget_flexibility": 0.2}',
    ARRAY['Meeting with clients', 'Conference attendance'],
    '{"preferred_flight_class": "business", "accommodation_type": "business_hotel", "activities": ["business", "networking"]}'
);

-- ===========================
-- SAMPLE FLIGHT DATA
-- ===========================

-- Insert sample flight options
INSERT INTO flights (
    trip_id,
    origin,
    destination,
    departure_date,
    return_date,
    flight_class,
    price,
    currency,
    airline,
    flight_number,
    booking_status,
    metadata
) VALUES 
(
    1, -- Japan trip
    'LAX',
    'NRT',
    '2025-07-15',
    '2025-07-30',
    'economy',
    1200.00,
    'USD',
    'Japan Airlines',
    'JL062',
    'available',
    '{"duration": "11h 30m", "stops": 0, "aircraft": "Boeing 787"}'
),
(
    2, -- NY business trip
    'LAX',
    'JFK',
    '2025-08-10',
    '2025-08-15',
    'business',
    800.00,
    'USD',
    'American Airlines',
    'AA124',
    'booked',
    '{"duration": "5h 45m", "stops": 0, "aircraft": "Airbus A321"}'
);

-- ===========================
-- SAMPLE ACCOMMODATION DATA
-- ===========================

-- Insert sample accommodation options
INSERT INTO accommodations (
    trip_id,
    name,
    address,
    check_in_date,
    check_out_date,
    room_type,
    price_per_night,
    total_price,
    currency,
    rating,
    amenities,
    booking_status,
    metadata
) VALUES 
(
    1, -- Japan trip
    'Park Hyatt Tokyo',
    '3-7-1-2 Nishi-Shinjuku, Shinjuku, Tokyo, Japan',
    '2025-07-15',
    '2025-07-30',
    'Deluxe Room',
    400.00,
    6000.00,
    'USD',
    4.8,
    ARRAY['WiFi', 'Spa', 'Restaurant', 'City View', 'Fitness Center'],
    'available',
    '{"cancellation_policy": "flexible", "breakfast_included": true}'
),
(
    2, -- NY business trip
    'The Plaza Hotel',
    '768 5th Ave, New York, NY 10019, USA',
    '2025-08-10',
    '2025-08-15',
    'Business Suite',
    600.00,
    3000.00,
    'USD',
    4.6,
    ARRAY['WiFi', 'Business Center', 'Restaurant', 'Spa', 'Concierge'],
    'booked',
    '{"cancellation_policy": "moderate", "breakfast_included": false}'
);

-- ===========================
-- SAMPLE CHAT SESSION DATA
-- ===========================

-- Insert sample chat sessions and messages
INSERT INTO chat_sessions (
    id,
    user_id,
    trip_id,
    metadata
) VALUES 
(
    '10000000-0000-0000-0000-000000000001'::UUID,
    '00000000-0000-0000-0000-000000000001'::UUID,
    1,
    '{"context": "trip_planning", "agent_mode": "comprehensive"}'
);

-- Insert sample chat messages
INSERT INTO chat_messages (
    session_id,
    role,
    content,
    metadata
) VALUES 
(
    '10000000-0000-0000-0000-000000000001'::UUID,
    'user',
    'I want to plan a trip to Japan for 2 people in July. Budget is around $5000.',
    '{"message_type": "trip_request"}'
),
(
    '10000000-0000-0000-0000-000000000001'::UUID,
    'assistant',
    'Great! I''d love to help you plan your trip to Japan. With a $5000 budget for 2 people in July, you''ll have wonderful options. Let me search for flights and accommodations for you.',
    '{"message_type": "trip_assistance", "tools_used": ["flight_search", "accommodation_search"]}'
);

-- ===========================
-- SAMPLE API KEYS DATA
-- ===========================

-- Insert sample API keys (encrypted dummy data for development)
INSERT INTO api_keys (
    user_id,
    service_name,
    key_name,
    encrypted_key,
    key_hash,
    is_active,
    metadata
) VALUES 
(
    '00000000-0000-0000-0000-000000000001'::UUID,
    'duffel',
    'production',
    'encrypted_dummy_key_for_development_testing',
    'hash_of_dummy_key',
    true,
    '{"environment": "sandbox", "capabilities": ["flights", "booking"]}'
),
(
    '00000000-0000-0000-0000-000000000001'::UUID,
    'google_maps',
    'places_api',
    'encrypted_dummy_places_api_key',
    'hash_of_places_key',
    true,
    '{"environment": "production", "capabilities": ["places", "geocoding", "directions"]}'
);

-- ===========================
-- SAMPLE MEMORY DATA
-- ===========================

-- Insert sample user memories (without embeddings for simplicity)
INSERT INTO memories (
    user_id,
    memory_type,
    content,
    metadata
) VALUES 
(
    '00000000-0000-0000-0000-000000000001',
    'user_preference',
    'User prefers economy class flights and values authentic cultural experiences over luxury accommodations.',
    '{"confidence": 0.8, "source": "trip_history"}'
),
(
    '00000000-0000-0000-0000-000000000001',
    'trip_history',
    'Previously traveled to Europe and Southeast Asia, enjoys planning trips 3-6 months in advance.',
    '{"confidence": 0.9, "source": "conversation_analysis"}'
);

-- ===========================
-- DEVELOPMENT DATA SUMMARY
-- ===========================

-- Log seed data completion
DO $$
BEGIN
    RAISE NOTICE 'TripSage Development Seed Data Loaded Successfully!';
    RAISE NOTICE 'Seed data includes:';
    RAISE NOTICE '- 👤 1 demo user (demo@tripsage.ai)';
    RAISE NOTICE '- ✈️  2 sample trips (Japan vacation, NY business)';
    RAISE NOTICE '- 🎫 2 flight options';
    RAISE NOTICE '- 🏨 2 accommodation options';
    RAISE NOTICE '- 💬 1 chat session with sample messages';
    RAISE NOTICE '- 🔑 2 API key entries (dummy data)';
    RAISE NOTICE '- 🧠 2 memory entries for personalization';
    RAISE NOTICE '';
    RAISE NOTICE 'Ready for development and testing! 🚀';
    RAISE NOTICE 'Access demo account: demo@tripsage.ai';
END $$;