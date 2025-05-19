# TripSage Relational Database Schema Details

This document provides detailed information about the TripSage relational database schema, primarily implemented in PostgreSQL and managed via Supabase (for production/staging) and Neon (for development).

## 1. Project Information

* **Project Name (Supabase Example)**: `tripsage_planner`
* **Database Type**: PostgreSQL (version 15+)

## 2. Schema Naming Conventions

* **Case**: Use `snake_case` for all table and column names (PostgreSQL standard).
* **Table Names**: Plural, lowercase, with underscores separating words (e.g., `trips`, `itinerary_items`).
* **Column Names**: Lowercase, with underscores.
* **Primary Keys**: Typically `id`. For `BIGINT GENERATED ALWAYS AS IDENTITY`, this is standard. If using UUIDs, `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` is common. The provided schema uses `BIGINT` for `users`, `trips`, etc., and `UUID` for others. Consistency is key; the examples below show a mix, which should be standardized (e.g., all `BIGINT` or all `UUID` for primary keys unless specific reasons dictate otherwise).
* **Foreign Keys**: Use the singular form of the referenced table with an `_id` suffix (e.g., `trip_id` in `flights` table referencing `trips.id`). Include `ON DELETE CASCADE` or `ON DELETE SET NULL` as appropriate.
* **Timestamps**: Include `created_at` and `updated_at` columns (type `TIMESTAMP WITH TIME ZONE`, often abbreviated as `TIMESTAMPTZ`) on all relevant tables.
  * `created_at`: `DEFAULT NOW() NOT NULL`
  * `updated_at`: `DEFAULT NOW() NOT NULL` (often updated by a trigger).
* **Indexes**: Prefix index names (e.g., `idx_trips_user_id`).
* **Comments**: Add `COMMENT ON TABLE ...` and `COMMENT ON COLUMN ...` for clarity, especially for complex fields or business rules.

## 3. Table Definitions

*(Note: The original schema used a mix of `BIGINT GENERATED ALWAYS AS IDENTITY` and `UUID` for primary keys. For consistency, this consolidated version will lean towards `BIGINT` for tables like `users` and `trips` as shown in `supabase_integration.md`, and `UUID` for others as shown in `schema_details.md`. A final project decision should standardize this, e.g., all UUIDs or all BIGINTs, unless there's a strong reason for mixed types.)*

*(The `user_id` in many tables should reference `auth.users(id)` if using Supabase Auth, which uses UUIDs. If `users` is a custom public table, then the FK type should match that `users.id` type.)*

### 3.1. `users`

Stores user profiles and preferences. (From `supabase_integration.md`)

| Column           | Type                     | Constraints                                     | Description                        |
|------------------|--------------------------|-------------------------------------------------|------------------------------------|
| `id`             | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`      | Unique identifier for the user.    |
| `auth_user_id`   | `UUID`                   | `NULLABLE REFERENCES auth.users(id) ON DELETE SET NULL` | Links to Supabase Auth user.     |
| `name`             | `TEXT`                   | `NULLABLE`                                      | User's full name.                  |
| `email`          | `TEXT`                   | `NOT NULL UNIQUE`                               | User's email address.              |
| `preferences_json`| `JSONB`                  | `NULLABLE`                                      | User travel preferences as JSON.   |
| `created_at`     | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Timestamp of user creation.        |
| `updated_at`     | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Timestamp of last user update.     |

```sql
-- SQL for users table
CREATE TABLE IF NOT EXISTS public.users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    auth_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- Link to Supabase auth.users
    name TEXT,
    email TEXT NOT NULL UNIQUE,
    preferences_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE public.users IS 'Stores user profiles and preferences, linking to Supabase authentication.';
```

### 3.2. `trips`

Stores primary information about user-planned trips. (Combined from `supabase_integration.md` and `schema_details.md`)

| Column        | Type                     | Constraints                                                              | Description                                                |
|---------------|--------------------------|--------------------------------------------------------------------------|------------------------------------------------------------|
| `id`          | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`                               | Unique identifier for the trip.                            |
| `user_id`     | `UUID`                   | `NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE`                   | Foreign key to the `auth.users` table (Supabase Auth).     |
| `name`        | `TEXT`                   | `NOT NULL`                                                               | Title of the trip.                                         |
| `start_date`  | `DATE`                   | `NOT NULL`                                                               | Start date of the trip.                                    |
| `end_date`    | `DATE`                   | `NOT NULL, CHECK (end_date >= start_date)`                               | End date of the trip.                                      |
| `destination` | `TEXT`                   | `NOT NULL`                                                               | Primary destination of the trip.                           |
| `budget`      | `NUMERIC`                | `NOT NULL, CHECK (budget > 0)`                                           | Total budget for the trip.                                 |
| `travelers`   | `INTEGER`                | `NOT NULL DEFAULT 1, CHECK (travelers > 0)`                              | Number of travelers.                                       |
| `status`      | `TEXT`                   | `NOT NULL DEFAULT 'planning', CHECK (status IN ('planning', 'booked', 'completed', 'canceled'))` | Current status of the trip.              |
| `trip_type`   | `TEXT`                   | `NOT NULL DEFAULT 'leisure', CHECK (trip_type IN ('leisure', 'business', 'family', 'solo', 'other'))` | Type of the trip.                         |
| `flexibility` | `JSONB`                  | `NULLABLE`                                                               | Flexibility parameters (e.g., date range, budget range).   |
| `description` | `TEXT`                   | `NULLABLE`                                                               | Optional longer description of the trip.                   |
| `created_at`  | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                                                 | Timestamp of trip creation.                                |
| `updated_at`  | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                                                 | Timestamp of last trip update.                             |

```sql
-- SQL for trips table
CREATE TABLE IF NOT EXISTS public.trips (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    destination TEXT NOT NULL,
    budget NUMERIC NOT NULL,
    travelers INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'planning',
    trip_type TEXT NOT NULL DEFAULT 'leisure',
    flexibility JSONB,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT trips_date_check CHECK (end_date >= start_date),
    CONSTRAINT trips_travelers_check CHECK (travelers > 0),
    CONSTRAINT trips_budget_check CHECK (budget > 0),
    CONSTRAINT trips_status_check CHECK (status IN ('planning', 'booked', 'completed', 'canceled')),
    CONSTRAINT trips_type_check CHECK (trip_type IN ('leisure', 'business', 'family', 'solo', 'other'))
);
COMMENT ON TABLE public.trips IS 'Stores primary information about user-planned trips.';
COMMENT ON COLUMN public.trips.flexibility IS 'JSONB field for storing flexibility preferences, e.g., date ranges, budget flexibility.';
```

### 3.3. `flights`

Stores flight information related to trips. (From `supabase_integration.md`)

| Column            | Type                     | Constraints                                     | Description                                      |
|-------------------|--------------------------|-------------------------------------------------|--------------------------------------------------|
| `id`              | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`      | Unique identifier for the flight record.         |
| `trip_id`         | `BIGINT`                 | `NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE` | Foreign key to the `trips` table.                |
| `origin`          | `TEXT`                   | `NOT NULL`                                      | Origin airport/city code (e.g., IATA).           |
| `destination`     | `TEXT`                   | `NOT NULL`                                      | Destination airport/city code (e.g., IATA).      |
| `airline`         | `TEXT`                   | `NULLABLE`                                      | Name of the airline.                             |
| `departure_time`  | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`                                      | Departure date and time with timezone.           |
| `arrival_time`    | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`                                      | Arrival date and time with timezone.             |
| `price`           | `NUMERIC`                | `NOT NULL, CHECK (price >= 0)`                  | Price of the flight.                             |
| `booking_link`    | `TEXT`                   | `NULLABLE`                                      | URL to the booking page or confirmation.         |
| `segment_number`  | `INTEGER`                | `NULLABLE`                                      | For multi-leg flights, the segment sequence.     |
| `search_timestamp`| `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Timestamp when this flight option was found.     |
| `booking_status`  | `TEXT`                   | `NOT NULL DEFAULT 'saved'`                      | Status like 'saved', 'booked', 'pending'.        |
| `data_source`     | `TEXT`                   | `NULLABLE`                                      | API or source from which flight data was fetched.|
| `created_at`      | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Timestamp of record creation.                    |
| `updated_at`      | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Timestamp of last record update.                 |

```sql
-- SQL for flights table
CREATE TABLE IF NOT EXISTS public.flights (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    airline TEXT,
    departure_time TIMESTAMP WITH TIME ZONE NOT NULL,
    arrival_time TIMESTAMP WITH TIME ZONE NOT NULL,
    price NUMERIC NOT NULL,
    booking_link TEXT,
    segment_number INTEGER,
    search_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    booking_status TEXT NOT NULL DEFAULT 'saved',
    data_source TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT flights_price_check CHECK (price >= 0)
);
COMMENT ON TABLE public.flights IS 'Stores flight information for trips.';
```

### 3.4. `accommodations`

Stores accommodation information for trips. (From `supabase_integration.md`)

| Column                | Type                     | Constraints                                     | Description                                         |
|-----------------------|--------------------------|-------------------------------------------------|-----------------------------------------------------|
| `id`                  | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`      | Unique identifier for the accommodation record.     |
| `trip_id`             | `BIGINT`                 | `NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE` | Foreign key to the `trips` table.                   |
| `name`                | `TEXT`                   | `NOT NULL`                                      | Name of the accommodation.                          |
| `type`                | `TEXT`                   | `NOT NULL`                                      | Type (e.g., 'hotel', 'airbnb', 'hostel').           |
| `check_in_date`       | `DATE`                   | `NOT NULL`                                      | Check-in date.                                      |
| `check_out_date`      | `DATE`                   | `NOT NULL, CHECK (check_out_date >= check_in_date)` | Check-out date.                                    |
| `price_per_night`     | `NUMERIC`                | `NOT NULL, CHECK (price_per_night >= 0)`        | Price per night.                                    |
| `total_price`         | `NUMERIC`                | `NOT NULL, CHECK (total_price >= 0)`            | Total price for the stay.                           |
| `location`            | `TEXT`                   | `NOT NULL`                                      | Address or general location of the accommodation.   |
| `rating`              | `NUMERIC`                | `NULLABLE, CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5))` | User or platform rating (e.g., 0-5 stars).        |
| `amenities`           | `JSONB`                  | `NULLABLE`                                      | List of amenities as JSON.                          |
| `booking_link`        | `TEXT`                   | `NULLABLE`                                      | URL to the booking page or confirmation.            |
| `search_timestamp`    | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Timestamp when this accommodation option was found. |
| `booking_status`      | `TEXT`                   | `NOT NULL DEFAULT 'saved'`                      | Status like 'saved', 'booked', 'pending'.           |
| `cancellation_policy` | `TEXT`                   | `NULLABLE`                                      | Cancellation policy details.                        |
| `distance_to_center`  | `NUMERIC`                | `NULLABLE`                                      | Distance to city center (e.g., in km).              |
| `neighborhood`        | `TEXT`                   | `NULLABLE`                                      | Neighborhood or area.                               |
| `created_at`          | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Timestamp of record creation.                       |
| `updated_at`          | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Timestamp of last record update.                    |

```sql
-- SQL for accommodations table
CREATE TABLE IF NOT EXISTS public.accommodations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- e.g., 'hotel', 'airbnb', 'hostel'
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    price_per_night NUMERIC NOT NULL,
    total_price NUMERIC NOT NULL,
    location TEXT NOT NULL,
    rating NUMERIC,
    amenities JSONB,
    booking_link TEXT,
    search_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    booking_status TEXT NOT NULL DEFAULT 'saved',
    cancellation_policy TEXT,
    distance_to_center NUMERIC, -- e.g., in km
    neighborhood TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT accommodations_date_check CHECK (check_out_date >= check_in_date),
    CONSTRAINT accommodations_price_per_night_check CHECK (price_per_night >= 0),
    CONSTRAINT accommodations_total_price_check CHECK (total_price >= 0),
    CONSTRAINT accommodations_rating_check CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)) -- Assuming a 0-5 rating scale
);
COMMENT ON TABLE public.accommodations IS 'Stores accommodation options for trips.';
```

### 3.5. `transportation`

Stores local transportation options during trips. (From `schema_details.md`, adapted)

| Column            | Type                     | Constraints                                     | Description                                         |
|-------------------|--------------------------|-------------------------------------------------|-----------------------------------------------------|
| `id`              | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`      | Unique identifier.                                  |
| `trip_id`         | `BIGINT`                 | `NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE` | Foreign key to `trips`.                             |
| `type`            | `TEXT`                   | `NOT NULL`                                      | E.g., 'train', 'bus', 'taxi', 'rental_car', 'ferry'.|
| `origin`          | `TEXT`                   | `NOT NULL`                                      | Starting location.                                  |
| `destination`     | `TEXT`                   | `NOT NULL`                                      | Ending location.                                    |
| `departure_time`  | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`                                      | Departure time.                                     |
| `arrival_time`    | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`                                      | Arrival time.                                       |
| `price`           | `NUMERIC`                | `NOT NULL, CHECK (price >= 0)`                  | Price of the transportation.                        |
| `provider_name`   | `TEXT`                   | `NULLABLE`                                      | Name of the transport provider.                     |
| `booking_reference`| `TEXT`                  | `NULLABLE`                                      | Booking confirmation code.                          |
| `status`          | `TEXT`                   | `NOT NULL DEFAULT 'planned'`                    | E.g., 'planned', 'booked', 'cancelled'.             |
| `created_at`      | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Record creation timestamp.                          |
| `updated_at`      | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Record last update timestamp.                       |

```sql
-- SQL for transportation table
CREATE TABLE IF NOT EXISTS public.transportation (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    type TEXT NOT NULL, -- e.g., 'train', 'bus', 'taxi', 'rental_car', 'ferry'
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_time TIMESTAMP WITH TIME ZONE NOT NULL,
    arrival_time TIMESTAMP WITH TIME ZONE NOT NULL,
    price NUMERIC NOT NULL,
    provider_name TEXT,
    booking_reference TEXT,
    status TEXT NOT NULL DEFAULT 'planned', -- e.g., 'planned', 'booked', 'cancelled'
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT transportation_price_check CHECK (price >= 0),
    CONSTRAINT transportation_time_check CHECK (arrival_time >= departure_time)
);
COMMENT ON TABLE public.transportation IS 'Stores local transportation options during trips.';
```

### 3.6. `itinerary_items`

Stores detailed daily activities and events for a trip. (From `schema_details.md`, adapted)

| Column        | Type                     | Constraints                                     | Description                                      |
|---------------|--------------------------|-------------------------------------------------|--------------------------------------------------|
| `id`          | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`      | Unique identifier.                               |
| `trip_id`     | `BIGINT`                 | `NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE` | Foreign key to `trips`.                          |
| `day_number`  | `INTEGER`                | `NOT NULL, CHECK (day_number > 0)`              | Day of the trip (e.g., 1, 2, 3).                 |
| `start_time`  | `TIME WITHOUT TIME ZONE` | `NOT NULL`                                      | Start time of the activity (local to destination).|
| `end_time`    | `TIME WITHOUT TIME ZONE` | `NOT NULL`                                      | End time of the activity (local to destination).  |
| `title`       | `TEXT`                   | `NOT NULL`                                      | Title of the activity or event.                  |
| `description` | `TEXT`                   | `NULLABLE`                                      | Detailed description.                            |
| `location`    | `TEXT`                   | `NULLABLE`                                      | Location of the activity.                        |
| `category`    | `TEXT`                   | `NULLABLE`                                      | E.g., 'activity', 'meal', 'sightseeing', 'tour'. |
| `cost`        | `NUMERIC`                | `NULLABLE, CHECK (cost IS NULL OR cost >= 0)`   | Estimated cost of the item.                      |
| `priority`    | `INTEGER`                | `NULLABLE`                                      | Priority of the activity (e.g., 1-5).            |
| `notes`       | `TEXT`                   | `NULLABLE`                                      | Additional user notes for this item.             |
| `created_at`  | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Record creation timestamp.                       |
| `updated_at`  | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Record last update timestamp.                    |

```sql
-- SQL for itinerary_items table
CREATE TABLE IF NOT EXISTS public.itinerary_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL,
    start_time TIME WITHOUT TIME ZONE NOT NULL,
    end_time TIME WITHOUT TIME ZONE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    category TEXT, -- e.g., 'activity', 'meal', 'sightseeing', 'tour', 'transport'
    cost NUMERIC,
    priority INTEGER,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT itinerary_items_day_number_check CHECK (day_number > 0),
    CONSTRAINT itinerary_items_time_check CHECK (end_time >= start_time),
    CONSTRAINT itinerary_items_cost_check CHECK (cost IS NULL OR cost >= 0)
);
COMMENT ON TABLE public.itinerary_items IS 'Stores detailed daily activities and events for a trip.';
```

### 3.7. `search_history` (was `search_parameters`)

Records user search criteria for analytics and future recommendations. (From `required_changes.md`, adapted from `search_parameters`)

| Column          | Type                     | Constraints                                     | Description                                      |
|-----------------|--------------------------|-------------------------------------------------|--------------------------------------------------|
| `id`            | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`      | Unique identifier.                               |
| `user_id`       | `UUID`                   | `NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE` | Foreign key to `auth.users`.                     |
| `search_type`   | `TEXT`                   | `NOT NULL, CHECK (search_type IN ('flight', 'accommodation', 'activity', 'destination', 'general_web'))` | Type of search performed.                      |
| `search_params` | `JSONB`                  | `NOT NULL`                                      | Search parameters used by the user.              |
| `results_count` | `INTEGER`                | `NULLABLE`                                      | Number of results returned for the search.       |
| `created_at`    | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Timestamp when the search was performed.         |

```sql
-- SQL for search_history table
CREATE TABLE IF NOT EXISTS public.search_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    search_type TEXT NOT NULL, -- 'flight', 'accommodation', 'activity', 'destination', 'general_web'
    search_params JSONB NOT NULL,
    results_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT search_history_type_check CHECK (search_type IN ('flight', 'accommodation', 'activity', 'destination', 'general_web'))
);
COMMENT ON TABLE public.search_history IS 'History of user searches for analytics and recommendations.';
```

### 3.8. `price_history`

Stores historical price data for flights, accommodations, etc., for trend analysis. (From `schema_details.md`)

| Column      | Type                     | Constraints                                     | Description                                      |
|-------------|--------------------------|-------------------------------------------------|--------------------------------------------------|
| `id`        | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`      | Unique identifier.                               |
| `entity_type`| `TEXT`                  | `NOT NULL`                                      | Type of entity (e.g., 'flight', 'hotel').        |
| `entity_ref`| `TEXT`                  | `NOT NULL`                                      | Reference to the entity (e.g., flight route `SFO-JFK`, hotel ID). |
| `price`     | `NUMERIC`                | `NOT NULL, CHECK (price >= 0)`                  | Price at the recorded timestamp.                 |
| `currency`  | `TEXT`                   | `NOT NULL`                                      | Currency code (e.g., 'USD', 'EUR').              |
| `timestamp` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`                                      | Timestamp when the price was recorded.           |
| `source`    | `TEXT`                   | `NOT NULL`                                      | Source of the price information (e.g., API name).|
| `created_at`| `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Record creation timestamp.                       |

```sql
-- SQL for price_history table
CREATE TABLE IF NOT EXISTS public.price_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type TEXT NOT NULL, -- e.g., 'flight_route', 'hotel_room_type'
    entity_ref TEXT NOT NULL, -- e.g., 'SFO-JFK_2025-12-20', 'hotel_123_room_standard'
    price NUMERIC NOT NULL,
    currency TEXT NOT NULL, -- ISO 4217 currency code
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source TEXT NOT NULL, -- e.g., 'DuffelAPI', 'Booking.comScraper'
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT price_history_price_check CHECK (price >= 0)
);
CREATE INDEX IF NOT EXISTS idx_price_history_entity_ref_timestamp ON public.price_history (entity_ref, timestamp DESC);
COMMENT ON TABLE public.price_history IS 'Historical pricing data for various travel entities.';
```

### 3.9. `trip_notes`

Stores user-specific notes related to their trips. (From `schema_details.md`)

| Column     | Type                     | Constraints                                     | Description                                      |
|------------|--------------------------|-------------------------------------------------|--------------------------------------------------|
| `id`       | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`      | Unique identifier.                               |
| `trip_id`  | `BIGINT`                 | `NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE` | Foreign key to `trips`.                          |
| `user_id`  | `UUID`                   | `NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE` | Foreign key to `auth.users`.                     |
| `title`    | `TEXT`                   | `NOT NULL`                                      | Title of the note.                               |
| `content`  | `TEXT`                   | `NOT NULL`                                      | Content of the note.                             |
| `created_at`| `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Record creation timestamp.                       |
| `updated_at`| `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Record last update timestamp.                    |

```sql
-- SQL for trip_notes table
CREATE TABLE IF NOT EXISTS public.trip_notes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE public.trip_notes IS 'User-specific notes related to their trips.';
```

### 3.10. `saved_options`

Stores alternative travel options (flights, hotels) that users save during planning. (From `schema_details.md`)

| Column        | Type                     | Constraints                                     | Description                                      |
|---------------|--------------------------|-------------------------------------------------|--------------------------------------------------|
| `id`          | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`      | Unique identifier.                               |
| `trip_id`     | `BIGINT`                 | `NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE` | Foreign key to `trips`.                          |
| `user_id`     | `UUID`                   | `NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE` | Foreign key to `auth.users`.                     |
| `option_type` | `TEXT`                   | `NOT NULL`                                      | Type of option (e.g., 'flight', 'hotel').        |
| `option_data` | `JSONB`                  | `NOT NULL`                                      | Full data of the saved option.                   |
| `is_selected` | `BOOLEAN`                | `NOT NULL DEFAULT FALSE`                        | Whether this option was ultimately selected for the trip. |
| `created_at`  | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Record creation timestamp.                       |
| `updated_at`  | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Record last update timestamp.                    |

```sql
-- SQL for saved_options table
CREATE TABLE IF NOT EXISTS public.saved_options (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    option_type TEXT NOT NULL, -- e.g., 'flight', 'hotel', 'activity'
    option_data JSONB NOT NULL, -- Stores the full details of the saved option
    is_selected BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE public.saved_options IS 'Alternative travel options saved by users during planning.';```

### 3.11. `trip_comparisons` (was `trip_comparison`)

Stores data for comparing different trip configurations or options. (From `schema_details.md`)

| Column            | Type                     | Constraints                                     | Description                                      |
|-------------------|--------------------------|-------------------------------------------------|--------------------------------------------------|
| `id`              | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`      | Unique identifier.                               |
| `user_id`         | `UUID`                   | `NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE` | Foreign key to `auth.users`.                     |
| `title`           | `TEXT`                   | `NOT NULL`                                      | Title for the comparison.                        |
| `description`     | `TEXT`                   | `NULLABLE`                                      | Description of what is being compared.           |
| `comparison_data` | `JSONB`                  | `NOT NULL`                                      | Structured data representing the comparison (e.g., array of trip options with their attributes). |
| `created_at`      | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Record creation timestamp.                       |
| `updated_at`      | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Record last update timestamp.                    |
```sql
-- SQL for trip_comparisons table
CREATE TABLE IF NOT EXISTS public.trip_comparisons (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    comparison_data JSONB NOT NULL, -- Could store an array of trip configurations or specific options
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE public.trip_comparisons IS 'Stores data for comparing different trip configurations or options.';
```

### 3.12. `kg_entity_references` (was `kg_entities`)

Links relational data to entities in the Neo4j knowledge graph. (From `required_changes.md`)

| Column       | Type                     | Constraints                                     | Description                                      |
|--------------|--------------------------|-------------------------------------------------|--------------------------------------------------|
| `id`         | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`      | Unique identifier for the reference link.        |
| `entity_id`  | `TEXT`                   | `NOT NULL`                                      | Unique ID of the entity in the knowledge graph (e.g., `Destination:Paris`). |
| `entity_type`| `TEXT`                   | `NOT NULL`                                      | Type of the entity in the knowledge graph (e.g., 'Destination', 'Accommodation'). |
| `primary_db_table` | `TEXT`             | `NOT NULL`                                      | Name of the table in the primary relational DB.  |
| `primary_db_id`    | `TEXT`             | `NOT NULL`                                      | ID of the record in the primary relational DB (store as TEXT to accommodate UUIDs or BIGINTs). |
| `properties` | `JSONB`                  | `NULLABLE`                                      | Additional properties or metadata about the link or KG entity snapshot. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Timestamp of link creation.                      |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Timestamp of last link update.                   |

```sql
-- SQL for kg_entity_references table
CREATE TABLE IF NOT EXISTS public.kg_entity_references (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id TEXT NOT NULL, -- This would be the unique identifier used in Neo4j, e.g., "Destination:Paris"
    entity_type TEXT NOT NULL, -- e.g., "Destination", "Accommodation" from KG
    primary_db_table TEXT NOT NULL, -- e.g., "trips", "accommodations"
    primary_db_id TEXT NOT NULL, -- The ID from the primary_db_table (BIGINT or UUID, stored as TEXT for flexibility)
    properties JSONB, -- Optional: Store key properties from KG or sync status
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_kg_primary_db_link UNIQUE (primary_db_table, primary_db_id, entity_type) -- Ensure one KG link per primary DB record of a certain type
);
CREATE INDEX IF NOT EXISTS idx_kg_entity_references_entity_id ON public.kg_entity_references (entity_id);
CREATE INDEX IF NOT EXISTS idx_kg_entity_references_primary_db ON public.kg_entity_references (primary_db_table, primary_db_id);
COMMENT ON TABLE public.kg_entity_references IS 'Links records from the relational database to corresponding entities in the Neo4j knowledge graph.';
```

### 3.13. `cache_items`

Generic table for caching API responses or computed data. (From `required_changes.md`)
*(Note: While Redis is the primary caching layer, this table could be used for more persistent, less volatile cached data if needed, or for specific types of caching not suited for Redis. However, for most application caching, Redis is preferred.)*

| Column      | Type                     | Constraints                                     | Description                                      |
|-------------|--------------------------|-------------------------------------------------|--------------------------------------------------|
| `id`        | `BIGINT`                 | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY`      | Unique identifier.                               |
| `cache_key` | `TEXT`                   | `NOT NULL`                                      | Unique key for the cached item.                  |
| `cache_value`| `JSONB`                 | `NOT NULL`                                      | The cached data, stored as JSON.                 |
| `source`    | `TEXT`                   | `NOT NULL`                                      | Source of the cached data (e.g., API name, computation type). |
| `expires_at`| `TIMESTAMP WITH TIME ZONE` | `NOT NULL`                                      | Expiry timestamp for the cached item.            |
| `created_at`| `TIMESTAMP WITH TIME ZONE` | `NOT NULL DEFAULT NOW()`                        | Timestamp when the item was cached.              |

```sql
-- SQL for cache_items table (Consider if this is truly needed alongside Redis)
CREATE TABLE IF NOT EXISTS public.cache_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cache_key TEXT NOT NULL,
    cache_value JSONB NOT NULL,
    source TEXT NOT NULL, -- e.g., 'DuffelAPI_Search', 'OpenWeatherMap_Forecast'
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_cache_items_key_source UNIQUE (cache_key, source)
);
CREATE INDEX IF NOT EXISTS idx_cache_items_expires_at ON public.cache_items (expires_at);
COMMENT ON TABLE public.cache_items IS 'Stores cached API responses or computed data, for items not suitable for or as a supplement to Redis.';
```

## 4. Triggers and Functions

It's good practice to have a trigger to automatically update `updated_at` timestamps.

```sql
-- Generic trigger function to update 'updated_at' timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply this trigger to tables, e.g., for the 'trips' table:
CREATE TRIGGER trips_update_updated_at
BEFORE UPDATE ON public.trips
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

-- Repeat for other tables like users, flights, accommodations, etc.
```

## 5. Row Level Security (RLS)

RLS policies are crucial for multi-user applications. Examples are provided in the [Relational Database Guide](./RELATIONAL_DATABASE_GUIDE.md#71-row-level-security-rls). Ensure RLS is enabled and appropriate policies are created for all tables containing user-specific data.

This detailed schema provides a solid foundation for TripSage's relational data storage needs. Remember to create corresponding migration files for each table and its modifications.
