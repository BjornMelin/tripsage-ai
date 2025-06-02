# 🗄️ TripSage Database Schema Reference

> **Status**: ✅ **Production Ready** - PostgreSQL with pgvector Extension  
> **Platform**: Supabase (Production/Staging) + Neon (Development)  
> **Version**: PostgreSQL 15+ with unified schema design

This comprehensive reference document provides detailed information about the TripSage relational database schema, including table definitions, relationships, constraints, and indexing strategies.

## 📋 Table of Contents

- [Project Information](#project-information)
- [Schema Design Principles](#schema-design-principles)
- [Core Tables](#core-tables)
- [Travel-Specific Tables](#travel-specific-tables)
- [Supporting Tables](#supporting-tables)
- [Memory and Knowledge Graph](#memory-and-knowledge-graph)
- [Indexes and Performance](#indexes-and-performance)
- [Triggers and Functions](#triggers-and-functions)
- [Row Level Security](#row-level-security)

## 🏗️ Project Information

### **Database Configuration**
- **Project Name (Supabase)**: `tripsage_planner`
- **Database Type**: PostgreSQL (version 15+)
- **Extensions**: pgvector, uuid-ossp, citext
- **Production**: Supabase Cloud
- **Development**: Neon Database
- **Testing**: Local PostgreSQL with Docker

### **Schema Overview**
```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "citext";

-- Core schemas
CREATE SCHEMA IF NOT EXISTS auth;        -- Supabase authentication
CREATE SCHEMA IF NOT EXISTS public;     -- Application tables
CREATE SCHEMA IF NOT EXISTS memory;     -- AI memory and embeddings
```

## 📐 Schema Design Principles

### **Naming Conventions**
- **Case**: Use `snake_case` for all table and column names (PostgreSQL standard)
- **Table Names**: Plural, lowercase, with underscores separating words (e.g., `trips`, `itinerary_items`)
- **Column Names**: Lowercase, with underscores
- **Primary Keys**: Consistently use `BIGINT GENERATED ALWAYS AS IDENTITY` for core tables
- **Foreign Keys**: Use the singular form of the referenced table with an `_id` suffix (e.g., `trip_id`)
- **Timestamps**: Include `created_at` and `updated_at` columns on all tables
- **Indexes**: Prefix index names with table abbreviation (e.g., `idx_trips_user_id`)

### **Data Types Standards**
- **IDs**: `BIGINT GENERATED ALWAYS AS IDENTITY` for application tables, `UUID` for auth references
- **Timestamps**: `TIMESTAMP WITH TIME ZONE` (abbreviated as `TIMESTAMPTZ`)
- **Text**: `TEXT` for variable-length strings, `CITEXT` for case-insensitive
- **JSON**: `JSONB` for structured data with indexing capabilities
- **Vectors**: `vector(1536)` for embedding storage using pgvector

### **Constraint Patterns**
- **Check Constraints**: Validate data integrity (dates, prices, enums)
- **Foreign Key Constraints**: Maintain referential integrity with appropriate CASCADE rules
- **Unique Constraints**: Prevent data duplication where business logic requires
- **Not Null Constraints**: Enforce required fields consistently

## 👥 Core Tables

### **1. Users Table**

Stores user profiles and preferences with link to Supabase authentication.

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

COMMENT ON TABLE public.users IS 'User profiles and preferences, linking to Supabase authentication';
COMMENT ON COLUMN public.users.auth_user_id IS 'Links to Supabase auth.users table';
COMMENT ON COLUMN public.users.preferences_json IS 'User travel preferences and settings';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_auth_user_id ON public.users (auth_user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users (email);
```

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| `id` | `BIGINT` | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY` | Unique identifier for the user |
| `auth_user_id` | `UUID` | `NULLABLE REFERENCES auth.users(id) ON DELETE SET NULL` | Links to Supabase Auth user |
| `name` | `TEXT` | `NULLABLE` | User's full name |
| `email` | `TEXT` | `NOT NULL UNIQUE` | User's email address |
| `preferences_json` | `JSONB` | `NULLABLE` | User travel preferences as JSON |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Timestamp of user creation |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Timestamp of last user update |

### **2. API Keys Table**

Securely stores user-provided API keys for external services (BYOK - Bring Your Own Key).

```sql
CREATE TABLE IF NOT EXISTS public.api_keys (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    service_name TEXT NOT NULL,
    key_name TEXT NOT NULL,
    encrypted_value TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    usage_count BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT api_keys_user_service_key_unique UNIQUE (user_id, service_name, key_name)
);

COMMENT ON TABLE public.api_keys IS 'Encrypted storage of user-provided API keys for external services';
COMMENT ON COLUMN public.api_keys.encrypted_value IS 'AES-256 encrypted API key value';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON public.api_keys (user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_service_name ON public.api_keys (service_name);
```

### **3. Chat Sessions Table**

Manages AI chat sessions for travel planning conversations.

```sql
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New Chat',
    context_data JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_message_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.chat_sessions IS 'AI chat sessions for travel planning conversations';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON public.chat_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_last_message_at ON public.chat_sessions (last_message_at DESC);
```

### **4. Chat Messages Table**

Stores individual messages within chat sessions.

```sql
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.chat_messages IS 'Individual messages within chat sessions';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON public.chat_messages (session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON public.chat_messages (created_at);
```

## ✈️ Travel-Specific Tables

### **1. Trips Table**

Core table storing trip information and planning details.

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

COMMENT ON TABLE public.trips IS 'Core trip information and planning details';
COMMENT ON COLUMN public.trips.flexibility IS 'JSONB field for storing flexibility preferences (date ranges, budget flexibility)';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_trips_user_id ON public.trips (user_id);
CREATE INDEX IF NOT EXISTS idx_trips_status ON public.trips (status);
CREATE INDEX IF NOT EXISTS idx_trips_start_date ON public.trips (start_date);
```

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| `id` | `BIGINT` | `GENERATED ALWAYS AS IDENTITY PRIMARY KEY` | Unique identifier for the trip |
| `user_id` | `UUID` | `NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE` | Foreign key to auth.users table |
| `name` | `TEXT` | `NOT NULL` | Title of the trip |
| `start_date` | `DATE` | `NOT NULL` | Start date of the trip |
| `end_date` | `DATE` | `NOT NULL, CHECK (end_date >= start_date)` | End date of the trip |
| `destination` | `TEXT` | `NOT NULL` | Primary destination of the trip |
| `budget` | `NUMERIC` | `NOT NULL, CHECK (budget > 0)` | Total budget for the trip |
| `travelers` | `INTEGER` | `NOT NULL DEFAULT 1, CHECK (travelers > 0)` | Number of travelers |
| `status` | `TEXT` | `NOT NULL DEFAULT 'planning'` | Current status (planning, booked, completed, canceled) |
| `trip_type` | `TEXT` | `NOT NULL DEFAULT 'leisure'` | Type of trip (leisure, business, family, solo, other) |
| `flexibility` | `JSONB` | `NULLABLE` | Flexibility parameters (date range, budget range) |
| `description` | `TEXT` | `NULLABLE` | Optional trip description |

### **2. Flights Table**

Stores flight information and booking details for trips.

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
    
    CONSTRAINT flights_price_check CHECK (price >= 0),
    CONSTRAINT flights_time_check CHECK (arrival_time >= departure_time)
);

COMMENT ON TABLE public.flights IS 'Flight information and booking details for trips';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_flights_trip_id ON public.flights (trip_id);
CREATE INDEX IF NOT EXISTS idx_flights_departure_time ON public.flights (departure_time);
CREATE INDEX IF NOT EXISTS idx_flights_origin_destination ON public.flights (origin, destination);
```

### **3. Accommodations Table**

Stores accommodation options and booking information.

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

COMMENT ON TABLE public.accommodations IS 'Accommodation options and booking information';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_accommodations_trip_id ON public.accommodations (trip_id);
CREATE INDEX IF NOT EXISTS idx_accommodations_check_in_date ON public.accommodations (check_in_date);
CREATE INDEX IF NOT EXISTS idx_accommodations_type ON public.accommodations (type);
```

### **4. Transportation Table**

Local transportation options during trips.

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

COMMENT ON TABLE public.transportation IS 'Local transportation options during trips';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_transportation_trip_id ON public.transportation (trip_id);
CREATE INDEX IF NOT EXISTS idx_transportation_type ON public.transportation (type);
```

### **5. Itinerary Items Table**

Detailed daily activities and events for trips.

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

COMMENT ON TABLE public.itinerary_items IS 'Detailed daily activities and events for trips';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_itinerary_items_trip_id ON public.itinerary_items (trip_id);
CREATE INDEX IF NOT EXISTS idx_itinerary_items_day_number ON public.itinerary_items (trip_id, day_number);
```

## 📊 Supporting Tables

### **1. Search History Table**

Records user search criteria for analytics and recommendations.

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

COMMENT ON TABLE public.search_history IS 'User search history for analytics and recommendations';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON public.search_history (user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_search_type ON public.search_history (search_type);
CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON public.search_history (created_at DESC);
```

### **2. Price History Table**

Historical price data for trend analysis and deal detection.

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

COMMENT ON TABLE public.price_history IS 'Historical pricing data for travel entities and trend analysis';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_price_history_entity_ref_timestamp ON public.price_history (entity_ref, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_entity_type ON public.price_history (entity_type);
```

### **3. Trip Notes Table**

User-specific notes related to trips.

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

COMMENT ON TABLE public.trip_notes IS 'User-specific notes related to trips';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_trip_notes_trip_id ON public.trip_notes (trip_id);
CREATE INDEX IF NOT EXISTS idx_trip_notes_user_id ON public.trip_notes (user_id);
```

### **4. Saved Options Table**

Alternative travel options saved during planning.

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

COMMENT ON TABLE public.saved_options IS 'Alternative travel options saved during planning';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_saved_options_trip_id ON public.saved_options (trip_id);
CREATE INDEX IF NOT EXISTS idx_saved_options_user_id ON public.saved_options (user_id);
CREATE INDEX IF NOT EXISTS idx_saved_options_type ON public.saved_options (option_type);
```

### **5. Trip Comparisons Table**

Data for comparing different trip configurations.

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

COMMENT ON TABLE public.trip_comparisons IS 'Data for comparing different trip configurations';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_trip_comparisons_user_id ON public.trip_comparisons (user_id);
```

## 🧠 Memory and Knowledge Graph

### **1. Memory Embeddings Table**

Stores AI memory embeddings for semantic search and context.

```sql
CREATE TABLE IF NOT EXISTS public.memory_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content_text TEXT NOT NULL,
    content_type TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.memory_embeddings IS 'AI memory embeddings for semantic search and context';

-- Vector similarity search index (HNSW)
CREATE INDEX IF NOT EXISTS idx_memory_embeddings_hnsw 
ON public.memory_embeddings 
USING hnsw (embedding vector_cosine_ops);

-- Standard indexes
CREATE INDEX IF NOT EXISTS idx_memory_embeddings_user_id ON public.memory_embeddings (user_id);
CREATE INDEX IF NOT EXISTS idx_memory_embeddings_content_type ON public.memory_embeddings (content_type);
```

### **2. KG Entity References Table**

Links relational data to knowledge graph entities.

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

COMMENT ON TABLE public.kg_entity_references IS 'Links relational database records to knowledge graph entities';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_kg_entity_references_entity_id ON public.kg_entity_references (entity_id);
CREATE INDEX IF NOT EXISTS idx_kg_entity_references_primary_db ON public.kg_entity_references (primary_db_table, primary_db_id);
```

## 🚀 Indexes and Performance

### **Primary Performance Indexes**

```sql
-- User-centric queries
CREATE INDEX IF NOT EXISTS idx_trips_user_status_date ON public.trips (user_id, status, start_date);
CREATE INDEX IF NOT EXISTS idx_flights_trip_departure ON public.flights (trip_id, departure_time);
CREATE INDEX IF NOT EXISTS idx_accommodations_trip_checkin ON public.accommodations (trip_id, check_in_date);

-- Search and filtering
CREATE INDEX IF NOT EXISTS idx_price_history_entity_timestamp ON public.price_history (entity_type, entity_ref, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_search_history_user_type_date ON public.search_history (user_id, search_type, created_at DESC);

-- Chat and messaging
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON public.chat_messages (session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_active ON public.chat_sessions (user_id, is_active, last_message_at DESC);

-- Vector search optimization
CREATE INDEX IF NOT EXISTS idx_memory_embeddings_user_type ON public.memory_embeddings (user_id, content_type);
```

### **Composite Indexes for Common Queries**

```sql
-- Trip planning workflows
CREATE INDEX IF NOT EXISTS idx_trips_planning_workflow 
ON public.trips (user_id, status) 
WHERE status IN ('planning', 'booked');

-- Price tracking and analysis
CREATE INDEX IF NOT EXISTS idx_price_history_analysis 
ON public.price_history (entity_type, timestamp DESC) 
WHERE timestamp > NOW() - INTERVAL '90 days';

-- Active chat sessions
CREATE INDEX IF NOT EXISTS idx_active_chat_sessions 
ON public.chat_sessions (user_id, last_message_at DESC) 
WHERE is_active = true;
```

## ⚙️ Triggers and Functions

### **1. Updated At Trigger Function**

Automatically updates `updated_at` timestamps.

```sql
-- Generic trigger function to update 'updated_at' timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at column
CREATE TRIGGER users_update_updated_at
BEFORE UPDATE ON public.users
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER trips_update_updated_at
BEFORE UPDATE ON public.trips
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER flights_update_updated_at
BEFORE UPDATE ON public.flights
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER accommodations_update_updated_at
BEFORE UPDATE ON public.accommodations
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

-- Continue for other tables...
```

### **2. Chat Session Management**

Automatically update chat session activity.

```sql
-- Function to update chat session last_message_at
CREATE OR REPLACE FUNCTION public.update_chat_session_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.chat_sessions 
    SET last_message_at = NEW.created_at
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update session activity on new messages
CREATE TRIGGER chat_messages_update_session_activity
AFTER INSERT ON public.chat_messages
FOR EACH ROW
EXECUTE FUNCTION public.update_chat_session_activity();
```

### **3. Price History Cleanup**

Automatically clean up old price history data.

```sql
-- Function to clean up old price history
CREATE OR REPLACE FUNCTION public.cleanup_old_price_history()
RETURNS void AS $$
BEGIN
    DELETE FROM public.price_history 
    WHERE created_at < NOW() - INTERVAL '1 year';
END;
$$ LANGUAGE plpgsql;

-- Schedule daily cleanup (requires pg_cron extension)
-- SELECT cron.schedule('cleanup-price-history', '0 2 * * *', 'SELECT public.cleanup_old_price_history();');
```

## 🔒 Row Level Security

### **RLS Policies for User Data Protection**

```sql
-- Enable RLS on all user-specific tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.flights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accommodations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_embeddings ENABLE ROW LEVEL SECURITY;

-- Users can only access their own data
CREATE POLICY "Users can view own profile" ON public.users
FOR SELECT USING (auth.uid() = auth_user_id);

CREATE POLICY "Users can update own profile" ON public.users
FOR UPDATE USING (auth.uid() = auth_user_id);

-- Trips access policies
CREATE POLICY "Users can view own trips" ON public.trips
FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own trips" ON public.trips
FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own trips" ON public.trips
FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own trips" ON public.trips
FOR DELETE USING (auth.uid() = user_id);

-- Flights access through trip ownership
CREATE POLICY "Users can view flights for own trips" ON public.flights
FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM public.trips 
        WHERE trips.id = flights.trip_id 
        AND trips.user_id = auth.uid()
    )
);

-- Similar policies for accommodations, transportation, etc.
CREATE POLICY "Users can view accommodations for own trips" ON public.accommodations
FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM public.trips 
        WHERE trips.id = accommodations.trip_id 
        AND trips.user_id = auth.uid()
    )
);

-- Chat sessions and messages
CREATE POLICY "Users can view own chat sessions" ON public.chat_sessions
FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view messages from own sessions" ON public.chat_messages
FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM public.chat_sessions 
        WHERE chat_sessions.id = chat_messages.session_id 
        AND chat_sessions.user_id = auth.uid()
    )
);

-- Memory embeddings
CREATE POLICY "Users can view own memory embeddings" ON public.memory_embeddings
FOR SELECT USING (auth.uid() = user_id);
```

### **Service Role Policies**

```sql
-- Allow service role to access all data for system operations
CREATE POLICY "Service role has full access" ON public.users
FOR ALL USING (current_setting('role') = 'service_role');

CREATE POLICY "Service role has full access" ON public.trips
FOR ALL USING (current_setting('role') = 'service_role');

-- Continue for other tables...
```

## 📈 Performance Monitoring

### **Query Performance Views**

```sql
-- View for monitoring slow queries
CREATE OR REPLACE VIEW public.slow_queries AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements 
WHERE mean_time > 100  -- Queries taking more than 100ms on average
ORDER BY mean_time DESC;

-- View for monitoring table sizes
CREATE OR REPLACE VIEW public.table_sizes AS
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_stats
JOIN pg_class ON pg_stats.tablename = pg_class.relname
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

*This comprehensive database schema provides the foundation for TripSage's robust travel planning platform, supporting user management, trip planning, AI memory, and performance optimization with PostgreSQL and pgvector capabilities.*