# Supabase Schema & Data Architecture

> **Target Audience**: Data architects, database engineers, technical leads
> **Status**: Production Ready - Unified Supabase PostgreSQL Architecture

This document describes TripSage's Supabase PostgreSQL schema design, data models, and database architecture decisions. For implementation details and schema definitions, see the database migration files in `supabase/migrations/`.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Database Design](#database-design)
- [Core Data Models](#core-data-models)
- [Memory and AI Systems](#memory-and-ai-systems)
- [Security and Access Control](#security-and-access-control)
- [Performance and Indexing](#performance-and-indexing)
- [Schema Migration Strategy](#schema-migration-strategy)

## Architecture Overview

TripSage uses a unified Supabase PostgreSQL architecture with integrated extensions for all data persistence needs.

```mermaid
graph TB
    subgraph "Application Layer"
        API[FastAPI Backend]
        FE[Next.js Frontend]
    end

    subgraph "Supabase PostgreSQL"
        DB[(PostgreSQL Database)]
        RT[Realtime Engine]
        ST[Storage Engine]
        AUTH[Authentication]
        VAULT[Vault Encryption]
    end

    subgraph "AI & Memory"
        MEM0[Mem0 SDK]
        VECTOR[pgvector Extension]
    end

    subgraph "External Services"
        OPENAI[OpenAI API]
        REDIS[Redis Cache]
    end

    API --> DB
    FE --> RT
    API --> ST
    API --> AUTH
    API --> VAULT
    API --> MEM0
    DB --> VECTOR
    API --> OPENAI
    API --> REDIS
```

### Key Components

- **Supabase PostgreSQL**: Primary database with extensions
- **pgvector**: Vector similarity search for embeddings
- **Mem0**: External memory management SDK
- **Vault**: Encrypted API key storage
- **Realtime**: Live data synchronization
- **Storage**: File attachment management

## Database Design

### Schema Organization

The database uses a modular schema design with clear separation of concerns:

- **Core Trip Management**: `trips`, `flights`, `accommodations`, `transportation`, `itinerary_items`
- **Chat System**: `chat_sessions`, `chat_messages`, `chat_tool_calls`
- **Memory System**: `memories`, `session_memories`
- **Collaboration**: `trip_collaborators`
- **Search Cache**: `search_*` tables for performance optimization
- **Security**: `api_keys` with Vault integration

### Table Naming Conventions

- Primary keys: `BIGINT GENERATED ALWAYS AS IDENTITY`
- Foreign keys: Named `{table}_id` with appropriate references
- Timestamps: `created_at`, `updated_at` with timezone
- Status fields: Enum constraints with allowed values
- Metadata: `JSONB` for flexible extensions

## Core Data Models

### Trip Management

```sql
CREATE TABLE trips (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    destination TEXT NOT NULL,
    budget NUMERIC NOT NULL,
    travelers INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'planning',
    trip_type TEXT NOT NULL DEFAULT 'leisure',
    flexibility JSONB DEFAULT '{}',
    notes TEXT[],
    search_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT trips_date_check CHECK (end_date >= start_date),
    CONSTRAINT trips_travelers_check CHECK (travelers > 0),
    CONSTRAINT trips_budget_check CHECK (budget > 0),
    CONSTRAINT trips_status_check CHECK (status IN ('planning', 'booked', 'completed', 'cancelled')),
    CONSTRAINT trips_type_check CHECK (trip_type IN ('leisure', 'business', 'family', 'solo', 'other'))
);
```

### Travel Options

```sql
CREATE TABLE flights (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date DATE NOT NULL,
    return_date DATE,
    flight_class TEXT NOT NULL DEFAULT 'economy',
    price NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    airline TEXT,
    flight_number TEXT,
    booking_status TEXT NOT NULL DEFAULT 'available',
    external_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT flights_price_check CHECK (price >= 0),
    CONSTRAINT flights_class_check CHECK (flight_class IN ('economy', 'premium_economy', 'business', 'first')),
    CONSTRAINT flights_status_check CHECK (booking_status IN ('available', 'reserved', 'booked', 'cancelled'))
);

CREATE TABLE accommodations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    address TEXT,
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    room_type TEXT,
    price_per_night NUMERIC NOT NULL,
    total_price NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    rating NUMERIC,
    amenities TEXT[],
    booking_status TEXT NOT NULL DEFAULT 'available',
    external_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT accommodations_price_check CHECK (price_per_night >= 0 AND total_price >= 0),
    CONSTRAINT accommodations_dates_check CHECK (check_out_date > check_in_date),
    CONSTRAINT accommodations_rating_check CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)),
    CONSTRAINT accommodations_status_check CHECK (booking_status IN ('available', 'reserved', 'booked', 'cancelled'))
);
```

### Chat System

```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    trip_id BIGINT REFERENCES trips(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE chat_messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',

    CONSTRAINT chat_messages_role_check CHECK (role IN ('user', 'assistant', 'system')),
    CONSTRAINT chat_messages_content_length CHECK (length(content) <= 32768)
);
```

## Memory and AI Systems

### Vector Storage

The memory system uses pgvector for similarity search with 1536-dimensional embeddings:

```sql
CREATE TABLE memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL DEFAULT 'user_preference',
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT memories_type_check CHECK (memory_type IN ('user_preference', 'trip_history', 'search_pattern', 'conversation_context', 'other'))
);

CREATE TABLE session_memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT session_memories_content_length CHECK (length(content) <= 8192)
);
```

### Vector Search Queries

```sql
-- Semantic similarity search
SELECT
    id,
    content,
    metadata,
    embedding <=> %s::vector AS similarity_score
FROM memories
WHERE user_id = %s
    AND memory_type = %s
ORDER BY embedding <=> %s::vector
LIMIT 10;
```

### Mem0 Integration

Memory operations are handled through the Mem0 SDK with automatic synchronization to PostgreSQL vector tables. The system provides:

- Long-term user preference storage
- Conversation context management
- Trip history insights
- Real-time memory updates

## Security and Access Control

### Row Level Security

All user data tables use Row Level Security (RLS) with owner-based policies:

```sql
-- Enable RLS on user data tables
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

-- Owner-only access policy
CREATE POLICY "owner_access" ON trips
    FOR ALL USING (auth.uid() = user_id);
```

### API Key Management

User API keys are stored encrypted in Supabase Vault:

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    service TEXT NOT NULL,
    vault_secret_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used TIMESTAMPTZ,
    CONSTRAINT api_keys_user_service_uniq UNIQUE (user_id, service)
);
```

Access is controlled through security definer functions that validate service role execution.

## Performance and Indexing

### Vector Indexing

HNSW indexing provides efficient similarity search:

```sql
CREATE INDEX idx_memories_embedding
ON memories USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200);

CREATE INDEX idx_session_memories_embedding
ON session_memories USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200);
```

### Query Optimization

Common query patterns are optimized with appropriate indexes:

```sql
-- Trip queries
CREATE INDEX idx_trips_user_dates ON trips(user_id, start_date, end_date);
CREATE INDEX idx_trips_status ON trips(status);

-- Chat performance
CREATE INDEX idx_chat_sessions_user_trip ON chat_sessions(user_id, trip_id);
CREATE INDEX idx_chat_messages_session_created ON chat_messages(session_id, created_at);

-- Search cache
CREATE INDEX idx_search_destinations_user_query ON search_destinations(user_id, query_hash);
```

### Connection Management

Database connections are managed through the DatabaseService with:

- Connection pooling via configuration
- Circuit breaker pattern for fault tolerance
- Rate limiting per user
- Query metrics and monitoring
- Automatic retry logic

## Schema Migration Strategy

### Single Source of Truth

Establish a single-source-of-truth schema (`supabase/schema.sql`) plus optional `seed.sql` that can create a brand-new Supabase project with all Tripsage AI capabilities in one command, eliminating conflicting migrations.

### Extension Strategy

| Extension | Required By | Notes |
| --- | --- | --- |
| `pgcrypto` | UUID generation, hashing | Needed for `gen_random_uuid()` PKs + API key hashes. |
| `pg_trgm` | fuzzy search, Supabase text search | Already used in search tables + caching. |
| `vector` | AI memories, accommodation embeddings | Standardize on `extensions.vector` with dimension 1536; avoid duplicate enables. |
| `pgjwt` | Supabase helpers | Already in base schema; keep for auth RPCs. |
| `pg_stat_statements` | DB monitoring | Provide default but optional. |
| `pg_net` | Webhook + outbound HTTP | Only enable if webhook functions still needed; otherwise drop. |
| `http` | Webhook functions (if using http extension) | Evaluate vs `pg_net` when finalizing send logic. |
| `pgsodium` or `supabase_vault` | BYOK/API keys | Choose based on project plan (Vault preferred). |
| `realtime` | Supabase realtime policies | Already required for topic helpers. |
| `pgmq` | Queueing (if still using) | Enable only if referenced functions remain. |

### Table Inventory (Target Schema)

| Domain | Tables | Notes |
| --- | --- | --- |
| Trip Core | trips, flights, accommodations, transportation, itinerary_items, bookings, trip_collaborators | Use UUID PKs; cascade delete on trip_id/user_id. |
| AI Memories & RAG | memories, session_memories, accommodation_embeddings | Rename RAG table to `accommodation_embeddings` (TEXT PK referencing provider hotelId), store vector(1536) + metadata + optional user_id. |
| Integrations / BYOK | user_gateway_configs, user_api_keys (vault-backed), api_gateway_configs, user_settings | Consolidate API key storage tables; only store vault path + hashed metadata. |
| Storage + Files | storage bucket records (insert rows), file_versions, file_processing_queue | Seed default buckets (uploads, itinerary-assets). |
| Telemetry / Webhooks | webhook_configs, webhook_logs, webhook_events, notifications, system_metrics | Keep only actively used ones. |
| Search Cache | search_destinations, search_activities, search_flights, search_hotels | Validate ongoing need; can drop if unused. |
| Misc Helpers | chat_sessions, chat_messages, chat_tool_calls, file_attachments | |

### Function / RPC Inventory

**Keep (actively used):**

- `match_accommodation_embeddings` (reads from `accommodation_embeddings`; accepts `vector(1536)`).
- Vault helpers: `insert_user_api_key`, `get_user_api_key`, `delete_user_api_key`, `touch_user_api_key`.
- Gateway config RPCs: `upsert_user_gateway_config`, `get_user_gateway_base_url`, `delete_user_gateway_config`, `get_user_allow_gateway_fallback`.
- Realtime helpers: `rt_topic_prefix`, `rt_topic_suffix`, `rt_is_session_member`.
- `update_updated_at_column` triggers for tables needing audit.

**Review / trim** (validate actual usage before porting)

- Massive suite of cleanup/maintenance functions in `20251027174600_base_schema.sql` (e.g., `optimize_vector_indexes`, `daily_cleanup_job`, webhook retry helpers). Keep only ones referenced by cron/policies.
- Search caching helpers (may duplicate functionality now handled in app code).
- Webhook execution helpers (`send_webhook_with_retry`, etc.) if app now uses Vercel Background Functions instead.

### RLS & Policy Plan

| Table / RPC | Intended Access |
|-------------|-----------------|
| trips | Owner + collaborators |
| chat_sessions | Owner only |
| memories | Owner only |
| api_keys | Owner only (via SECURITY DEFINER RPCs) |

## File Storage

File attachments are managed through Supabase Storage:

```sql
CREATE TABLE file_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    trip_id BIGINT REFERENCES trips(id) ON DELETE CASCADE,
    chat_message_id BIGINT REFERENCES chat_messages(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    bucket_name TEXT NOT NULL DEFAULT 'attachments',
    upload_status TEXT NOT NULL DEFAULT 'uploading',
    virus_scan_status TEXT DEFAULT 'pending',
    virus_scan_result JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT file_attachments_size_check CHECK (file_size > 0),
    CONSTRAINT file_attachments_upload_status_check CHECK (upload_status IN ('uploading', 'completed', 'failed')),
    CONSTRAINT file_attachments_virus_status_check CHECK (virus_scan_status IN ('pending', 'clean', 'infected', 'failed'))
);
```

---

This architecture provides a scalable, secure foundation for TripSage's travel planning platform with integrated AI capabilities and real-time features.
