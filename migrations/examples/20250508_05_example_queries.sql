-- Example Queries for TripSage Database
-- Description: Example SQL queries for common operations in the TripSage travel planning system
-- Created: 2025-05-08

-- 1. Create a new trip
INSERT INTO trips (
    name, 
    start_date, 
    end_date, 
    destination, 
    budget, 
    travelers, 
    status, 
    trip_type, 
    flexibility
) VALUES (
    'Summer Vacation in Paris',
    '2025-07-15',
    '2025-07-25',
    'Paris, France',
    3000.00,
    2,
    'planning',
    'leisure',
    '{"date_range": 3, "budget_range": 500}'
) RETURNING id;

-- 2. Add a flight option to a trip
INSERT INTO flights (
    trip_id,
    origin,
    destination,
    airline,
    departure_time,
    arrival_time,
    price,
    booking_link,
    segment_number,
    booking_status,
    data_source
) VALUES (
    1,  -- Replace with actual trip_id
    'JFK',
    'CDG',
    'Air France',
    '2025-07-15 10:00:00+00',
    '2025-07-15 22:30:00+00',
    850.00,
    'https://example.com/booking/flight123',
    1,
    'viewed',
    'Skyscanner API'
);

-- 3. Add an accommodation option to a trip
INSERT INTO accommodations (
    trip_id,
    name,
    type,
    check_in,
    check_out,
    price_per_night,
    total_price,
    location,
    rating,
    amenities,
    booking_link,
    booking_status,
    cancellation_policy,
    distance_to_center,
    neighborhood
) VALUES (
    1,  -- Replace with actual trip_id
    'Hotel de la Paix',
    'hotel',
    '2025-07-15',
    '2025-07-25',
    200.00,
    2000.00,
    'Paris, France',
    4.5,
    '{"wifi": true, "breakfast": true, "pool": false, "spa": true}',
    'https://example.com/booking/hotel456',
    'viewed',
    'Free cancellation up to 24 hours before check-in',
    1.5,
    'Le Marais'
);

-- 4. Get all trips in planning status
SELECT * FROM trips WHERE status = 'planning';

-- 5. Get all flights for a specific trip
SELECT * FROM flights WHERE trip_id = 1 ORDER BY price ASC;

-- 6. Get all accommodations for a specific trip, sorted by rating
SELECT * FROM accommodations WHERE trip_id = 1 ORDER BY rating DESC;

-- 7. Get total budget and current allocated amount for a trip
SELECT 
    t.id AS trip_id,
    t.name AS trip_name,
    t.budget AS total_budget,
    COALESCE(f.flight_cost, 0) AS flight_cost,
    COALESCE(a.accommodation_cost, 0) AS accommodation_cost,
    COALESCE(tr.transport_cost, 0) AS transport_cost,
    COALESCE(i.activity_cost, 0) AS activity_cost,
    (COALESCE(f.flight_cost, 0) + COALESCE(a.accommodation_cost, 0) + COALESCE(tr.transport_cost, 0) + COALESCE(i.activity_cost, 0)) AS total_allocated,
    (t.budget - (COALESCE(f.flight_cost, 0) + COALESCE(a.accommodation_cost, 0) + COALESCE(tr.transport_cost, 0) + COALESCE(i.activity_cost, 0))) AS remaining
FROM 
    trips t
LEFT JOIN (
    SELECT trip_id, SUM(price) AS flight_cost
    FROM flights
    WHERE booking_status = 'booked'
    GROUP BY trip_id
) f ON t.id = f.trip_id
LEFT JOIN (
    SELECT trip_id, SUM(total_price) AS accommodation_cost
    FROM accommodations
    WHERE booking_status = 'booked'
    GROUP BY trip_id
) a ON t.id = a.trip_id
LEFT JOIN (
    SELECT trip_id, SUM(price) AS transport_cost
    FROM transportation
    WHERE booking_status = 'booked'
    GROUP BY trip_id
) tr ON t.id = tr.trip_id
LEFT JOIN (
    SELECT trip_id, SUM(cost) AS activity_cost
    FROM itinerary_items
    WHERE type = 'activity' AND cost IS NOT NULL
    GROUP BY trip_id
) i ON t.id = i.trip_id
WHERE 
    t.id = 1;

-- 8. Track price changes for a specific flight
SELECT * FROM price_history 
WHERE entity_type = 'flight' AND entity_id = 1 
ORDER BY timestamp DESC;

-- 9. Get complete itinerary for a trip
SELECT * FROM itinerary_items
WHERE trip_id = 1
ORDER BY date, time;

-- 10. Save a flight option for later comparison
INSERT INTO saved_options (trip_id, option_type, option_id, notes)
VALUES (1, 'flight', 1, 'Good price but long layover');

-- 11. Get all saved options for a trip
SELECT 
    so.id,
    so.option_type,
    so.option_id,
    so.notes,
    CASE 
        WHEN so.option_type = 'flight' THEN 
            (SELECT json_build_object(
                'airline', airline,
                'origin', origin,
                'destination', destination,
                'departure_time', departure_time,
                'arrival_time', arrival_time,
                'price', price
            ) FROM flights WHERE id = so.option_id)
        WHEN so.option_type = 'accommodation' THEN 
            (SELECT json_build_object(
                'name', name,
                'type', type,
                'location', location,
                'check_in', check_in,
                'check_out', check_out,
                'price_per_night', price_per_night,
                'total_price', total_price,
                'rating', rating
            ) FROM accommodations WHERE id = so.option_id)
        WHEN so.option_type = 'transportation' THEN 
            (SELECT json_build_object(
                'type', type,
                'provider', provider,
                'pickup_date', pickup_date,
                'dropoff_date', dropoff_date,
                'price', price
            ) FROM transportation WHERE id = so.option_id)
        ELSE NULL
    END AS option_details
FROM 
    saved_options so
WHERE 
    trip_id = 1
ORDER BY 
    timestamp DESC;

-- 12. Update trip status
UPDATE trips SET status = 'booked' WHERE id = 1;

-- 13. Add a note to a trip
INSERT INTO trip_notes (trip_id, content)
VALUES (1, 'Remember to check if hotel has airport shuttle service');

-- 14. Add a price history record
INSERT INTO price_history (entity_type, entity_id, price)
VALUES ('flight', 1, 875.00);

-- 15. Create trip comparison data
INSERT INTO trip_comparison (trip_id, comparison_json)
VALUES (1, '{
    "options": [
        {
            "flight": 1,
            "accommodation": 1,
            "total_cost": 2850.00,
            "pros": ["Direct flight", "Central hotel location"],
            "cons": ["Higher price", "No breakfast included"]
        },
        {
            "flight": 2,
            "accommodation": 3,
            "total_cost": 2500.00,
            "pros": ["Lower price", "Breakfast included"],
            "cons": ["Layover", "Further from city center"]
        }
    ]
}');

-- 16. Retrieve price history trend for a destination
WITH date_series AS (
    SELECT generate_series(
        (SELECT MIN(search_timestamp)::date FROM flights WHERE destination = 'CDG'),
        (SELECT MAX(search_timestamp)::date FROM flights WHERE destination = 'CDG'),
        '1 day'::interval
    ) AS date
)
SELECT 
    date_series.date,
    ROUND(AVG(f.price), 2) AS avg_price,
    MIN(f.price) AS min_price,
    MAX(f.price) AS max_price,
    COUNT(f.id) AS num_options
FROM 
    date_series
LEFT JOIN 
    flights f ON date_series.date = f.search_timestamp::date AND f.destination = 'CDG'
GROUP BY 
    date_series.date
ORDER BY 
    date_series.date;

-- 17. Find trips within date range
SELECT * FROM trips
WHERE start_date >= '2025-06-01' AND end_date <= '2025-08-31';

-- 18. Get all search parameters for a trip
SELECT * FROM search_parameters
WHERE trip_id = 1
ORDER BY timestamp DESC;

-- 19. Find trips with similar destinations
SELECT * FROM trips
WHERE destination ILIKE '%paris%' OR destination ILIKE '%france%';

-- 20. Get trip summary
SELECT 
    t.*,
    COUNT(DISTINCT f.id) AS flight_options,
    COUNT(DISTINCT a.id) AS accommodation_options,
    COUNT(DISTINCT tr.id) AS transportation_options,
    COUNT(DISTINCT i.id) AS itinerary_items,
    COUNT(DISTINCT n.id) AS notes
FROM 
    trips t
LEFT JOIN 
    flights f ON t.id = f.trip_id
LEFT JOIN 
    accommodations a ON t.id = a.trip_id
LEFT JOIN 
    transportation tr ON t.id = tr.trip_id
LEFT JOIN 
    itinerary_items i ON t.id = i.trip_id
LEFT JOIN 
    trip_notes n ON t.id = n.trip_id
WHERE 
    t.id = 1
GROUP BY 
    t.id;