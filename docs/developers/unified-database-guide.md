# 🗄️ TripSage Database Development Guide

> **Status**: ✅ **Production Ready** - PostgreSQL with pgvector Extension  
> **Platform**: Supabase (Production/Staging/Development)  
> **Version**: PostgreSQL 15+ with unified schema design

This comprehensive guide provides complete information about TripSage's database architecture, schema design, operations, triggers, and optimization strategies. It covers everything developers need to work effectively with our PostgreSQL database system.

## 📋 Table of Contents

- [Database Architecture Overview](#database-architecture-overview)
- [Schema Design and Management](#schema-design-and-management)
- [Database Operations](#database-operations)
- [Triggers and Automation](#triggers-and-automation)
- [Performance Optimization](#performance-optimization)
- [Migration Patterns](#migration-patterns)

## Database Architecture Overview

### **Current Architecture Components**

TripSage has evolved to a unified database architecture that eliminates complexity while maximizing performance:

#### **Unified Database Layer**

- **Primary**: Supabase PostgreSQL 15+ with pgvector/pgvectorscale extensions
- **Vector Storage**: Native pgvector for 1536-dimensional embeddings with HNSW indexing
- **Memory System**: Mem0 v1.0+ with direct Supabase backend integration
- **Performance**: 471+ QPS throughput, <100ms vector search latency

#### **Enhanced Caching Layer**

- **Technology**: DragonflyDB (Redis-compatible with enhanced performance)
- **Performance**: 25x improvement over Redis for frequently accessed data
- **Integration**: Seamless Redis protocol compatibility with optimized memory management
- **Use Cases**: API response caching, search result caching, session management

#### **Removed Components (Deprecated)**

- ❌ **Neo4j Knowledge Graph**: Replaced by Mem0 + pgvector
- ❌ **Qdrant Vector Database**: Replaced by native pgvector
- ❌ **Neon PostgreSQL**: Consolidated into Supabase
- ❌ **Redis Cache**: Upgraded to DragonflyDB
- ❌ **Complex Dual-Storage Patterns**: Simplified to unified access

### **Database Configuration**

- **Project Name (Supabase)**: `tripsage_planner`
- **Database Type**: PostgreSQL (version 15+)
- **Extensions**: pgvector, uuid-ossp, citext
- **Environment**: Unified Supabase across development, staging, and production
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

## Schema Design and Management

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

### **Core Tables**

#### **1. Users Table**

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

#### **2. API Keys Table**

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

#### **3. Trips Table**

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

#### **4. Memory Embeddings Table**

Stores AI memory embeddings for semantic search and context using pgvector.

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

## Database Operations

### **Modern Database Operations with Supabase CLI**

**Current Operational Standard (June 2025)**  
**Migration Path**: From legacy migrations/ to supabase/ directory structure

#### **1. Local Development Setup**

```bash
# Initialize Supabase in project (if not already done)
supabase init

# Start local development environment
supabase start

# Link to remote project
supabase link --project-ref [your-project-ref]

# Pull remote schema to local
supabase db pull
```

#### **2. Creating and Managing Migrations**

```bash
# Create a new migration
supabase migration new add_travel_preferences

# This creates: supabase/migrations/[timestamp]_add_travel_preferences.sql

# Edit the migration file, then apply locally
supabase db reset

# Generate TypeScript types from schema
supabase gen types typescript --local > database.types.ts
```

#### **3. Production Deployment**

```bash
# Push migrations to production
supabase db push

# Verify deployment
supabase projects list
supabase db inspect
```

### **Migration File Organization**

**Current Structure:**

```text
supabase/
├── config.toml
├── migrations/
│   ├── 20250526_01_enable_pgvector_extensions.sql
│   ├── 20250527_01_mem0_memory_system.sql
│   └── [timestamp]_[description].sql
├── functions/ (Edge Functions)
└── seed.sql (Development seed data)
```

### **Best Practices for Modern Schema Management**

1. **Use Supabase CLI exclusively** for all database operations
2. **Test locally first** with `supabase db reset` before pushing
3. **Generate types** after schema changes with `supabase gen types`
4. **Version control** all migration files in supabase/migrations/
5. **Use descriptive names** for migration files
6. **Never edit applied migrations** - create new ones for changes

### **Common Operations**

```bash
# Reset local database to match remote
supabase db pull
supabase db reset

# Check migration status
supabase migration list

# Validate schema
supabase db lint

# Generate seed data
supabase db dump --data-only > supabase/seed.sql

# Backup production data
supabase db dump --remote > backup.sql
```

## Triggers and Automation

### **Trigger Categories**

#### **1. Timestamp Management Triggers**

Automatically update `updated_at` timestamps on record modifications.

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
```

**Tables with `updated_at` triggers:**

- trips, flights, accommodations, chat_sessions, api_keys
- memories, file_attachments, trip_collaborators, itinerary_items
- transportation, trip_notes, saved_options, trip_comparisons, price_history

#### **2. Collaboration Event Triggers**

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

#### **3. Cache Invalidation Triggers**

##### **notify_cache_invalidation**

- **Tables:** trips, flights, accommodations
- **Event:** INSERT, UPDATE, DELETE
- **Notification Channel:** `cache_invalidation`
- **Payload:**

```json
{
  "event_type": "cache_invalidation",
  "table_name": "trips",
  "record_id": "123",
  "operation": "UPDATE",
  "timestamp": "2025-01-06T12:00:00Z"
}
```

#### **4. Business Logic Triggers**

```sql
-- Function to clean up old price history
CREATE OR REPLACE FUNCTION public.cleanup_old_price_history()
RETURNS void AS $$
BEGIN
    DELETE FROM public.price_history 
    WHERE created_at < NOW() - INTERVAL '1 year';
END;
$$ LANGUAGE plpgsql;
```

### **Scheduled Jobs (pg_cron)**

#### **Daily Jobs**

```sql
-- Daily cleanup at 2 AM UTC
SELECT cron.schedule('daily-cleanup', '0 2 * * *', 'SELECT daily_cleanup_job();');

-- Weekly maintenance on Sundays at 3 AM UTC
SELECT cron.schedule('weekly-maintenance', '0 3 * * 0', 'SELECT weekly_maintenance_job();');

-- Monthly cleanup on the 1st at 4 AM UTC
SELECT cron.schedule('monthly-cleanup', '0 4 1 * *', 'SELECT monthly_cleanup_job();');
```

#### **Monitor Jobs**

```sql
-- View scheduled jobs
SELECT * FROM cron.job;

-- View job run history
SELECT * FROM cron.job_run_details 
ORDER BY start_time DESC 
LIMIT 50;
```

## Performance Optimization

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

### **Vector Search Optimization**

```sql
-- Optimize vector search with intelligent filtering
SELECT /*+ IndexScan(memory_embeddings idx_memory_hnsw) */
    content_text,
    metadata,
    embedding <=> %s::vector as similarity_score
FROM memory_embeddings 
WHERE user_id = %s 
    AND embedding <=> %s::vector < 0.8  -- Similarity threshold
ORDER BY embedding <=> %s::vector 
LIMIT 20;
```

### **Performance Achievements Summary**

**Vector Operations:**

- Search Latency: <100ms (target achieved)
- Throughput: 471+ QPS
- Accuracy: 26% improvement in memory operations
- Index Performance: 11x improvement with HNSW over basic approaches

**Overall System Performance:**

- Infrastructure Costs: 80% reduction ($6,000-9,600 annually)
- Operational Complexity: 80% reduction in management overhead
- Development Velocity: Unified workflows across all environments

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

## Migration Patterns

### **Environment Configuration**

```toml
# supabase/config.toml
[db]
port = 54322
shadow_port = 54320
major_version = 15

[db.extensions]
enabled = ["vector", "uuid-ossp", "pg_stat_statements"]

[auth]
enabled = true
external_providers = ["google", "github"]

[storage]
enabled = true
bucket_limit = 100
```

### **Row Level Security**

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

-- Memory embeddings
CREATE POLICY "Users can view own memory embeddings" ON public.memory_embeddings
FOR SELECT USING (auth.uid() = user_id);
```

### **Testing Triggers**

```sql
-- Test collaboration notification
INSERT INTO trip_collaborators (trip_id, user_id, added_by, permission_level)
VALUES (1, 'user-uuid', 'owner-uuid', 'view');

-- Test cache invalidation
UPDATE trips SET destination = 'New York' WHERE id = 1;

-- Test session expiration
UPDATE chat_sessions 
SET updated_at = NOW() - INTERVAL '25 hours' 
WHERE id = 'session-uuid';

-- Manually run cleanup jobs
SELECT daily_cleanup_job();
SELECT weekly_maintenance_job();
SELECT monthly_cleanup_job();
```

---

*This comprehensive database guide provides the foundation for TripSage's robust travel planning platform, supporting user management, trip planning, AI memory, and performance optimization with PostgreSQL and pgvector capabilities.*
