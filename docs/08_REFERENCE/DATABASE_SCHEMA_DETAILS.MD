# TripSage Relational Database Schema Details

This document provides detailed information about the TripSage relational database schema, primarily implemented in PostgreSQL and managed via Supabase (for production/staging) and Neon (for development).

## 1. Project Information

- **Project Name (Supabase Example)**: `tripsage_planner`
- **Database Type**: PostgreSQL (version 15+)

## 2. Schema Naming Conventions

- Lowercase, snake_case for tables and columns.
- Primary keys typically `id BIGINT GENERATED ALWAYS AS IDENTITY`.
- Timestamps: `created_at`, `updated_at` with `TIMESTAMPTZ`.
- Comments for tables/columns where helpful.

## 3. Table Definitions

### 3.1. `users`

```sql
CREATE TABLE IF NOT EXISTS public.users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    auth_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    name TEXT,
    email TEXT NOT NULL UNIQUE,
    preferences_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 3.2. `trips`

```sql
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
```

### 3.3. `flights`

```sql
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
```

### 3.4. `accommodations`

```sql
CREATE TABLE IF NOT EXISTS public.accommodations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
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
    distance_to_center NUMERIC,
    neighborhood TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT accommodations_date_check CHECK (check_out_date >= check_in_date),
    CONSTRAINT accommodations_price_per_night_check CHECK (price_per_night >= 0),
    CONSTRAINT accommodations_total_price_check CHECK (total_price >= 0),
    CONSTRAINT accommodations_rating_check CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5))
);
```

### 3.5. `transportation`

```sql
CREATE TABLE IF NOT EXISTS public.transportation (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_time TIMESTAMP WITH TIME ZONE NOT NULL,
    arrival_time TIMESTAMP WITH TIME ZONE NOT NULL,
    price NUMERIC NOT NULL,
    provider_name TEXT,
    booking_reference TEXT,
    status TEXT NOT NULL DEFAULT 'planned',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT transportation_price_check CHECK (price >= 0),
    CONSTRAINT transportation_time_check CHECK (arrival_time >= departure_time)
);
```

### 3.6. `itinerary_items`

```sql
CREATE TABLE IF NOT EXISTS public.itinerary_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL,
    start_time TIME WITHOUT TIME ZONE NOT NULL,
    end_time TIME WITHOUT TIME ZONE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    category TEXT,
    cost NUMERIC,
    priority INTEGER,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT itinerary_items_day_number_check CHECK (day_number > 0),
    CONSTRAINT itinerary_items_time_check CHECK (end_time >= start_time),
    CONSTRAINT itinerary_items_cost_check CHECK (cost IS NULL OR cost >= 0)
);
```

### 3.7. `search_history`

```sql
CREATE TABLE IF NOT EXISTS public.search_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    search_type TEXT NOT NULL,
    search_params JSONB NOT NULL,
    results_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT search_history_type_check CHECK (search_type IN ('flight', 'accommodation', 'activity', 'destination', 'general_web'))
);
```

### 3.8. `price_history`

```sql
CREATE TABLE IF NOT EXISTS public.price_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_ref TEXT NOT NULL,
    price NUMERIC NOT NULL,
    currency TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT price_history_price_check CHECK (price >= 0)
);
CREATE INDEX IF NOT EXISTS idx_price_history_entity_ref_timestamp ON public.price_history (entity_ref, timestamp DESC);
```

### 3.9. `trip_notes`

```sql
CREATE TABLE IF NOT EXISTS public.trip_notes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 3.10. `saved_options`

```sql
CREATE TABLE IF NOT EXISTS public.saved_options (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    option_type TEXT NOT NULL,
    option_data JSONB NOT NULL,
    is_selected BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 3.11. `trip_comparisons`

```sql
CREATE TABLE IF NOT EXISTS public.trip_comparisons (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    comparison_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 3.12. `kg_entity_references`

```sql
CREATE TABLE IF NOT EXISTS public.kg_entity_references (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    primary_db_table TEXT NOT NULL,
    primary_db_id TEXT NOT NULL,
    properties JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_kg_primary_db_link UNIQUE (primary_db_table, primary_db_id, entity_type)
);
CREATE INDEX IF NOT EXISTS idx_kg_entity_references_entity_id ON public.kg_entity_references (entity_id);
CREATE INDEX IF NOT EXISTS idx_kg_entity_references_primary_db ON public.kg_entity_references (primary_db_table, primary_db_id);
```

### 3.13. `cache_items`

```sql
CREATE TABLE IF NOT EXISTS public.cache_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cache_key TEXT NOT NULL,
    cache_value JSONB NOT NULL,
    source TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_cache_items_key_source UNIQUE (cache_key, source)
);
CREATE INDEX IF NOT EXISTS idx_cache_items_expires_at ON public.cache_items (expires_at);
```

## 4. Triggers and Functions

```sql
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## 5. Row Level Security (RLS)

Enable RLS and create appropriate policies for multi-user data privacy.

This schema forms the basis of TripSage's relational data storage.
