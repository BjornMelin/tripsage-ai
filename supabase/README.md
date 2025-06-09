# TripSage Supabase Database Schema

This directory contains the complete, production-ready database schema for TripSage, organized using modern Supabase best practices with declarative schema management.

## 📁 Directory Structure

```text
supabase/
├── schemas/                    # Declarative schema files (organized by concern)
│   ├── 00_extensions.sql      # Extensions (UUID, pgvector)
│   ├── 01_tables.sql          # Core tables and business logic
│   ├── 02_indexes.sql         # Performance-optimized indexes
│   ├── 03_functions.sql       # Utility functions and stored procedures
│   ├── 04_triggers.sql        # Automated triggers
│   ├── 05_policies.sql        # Row Level Security policies
│   └── 06_views.sql           # Common database views
├── migrations/                 # Generated migration files
│   └── 20250609_02_consolidated_production_schema.sql
├── tests/                      # Database tests (optional)
├── config.toml                 # Supabase CLI configuration
├── seed.sql                    # Development seed data
└── README.md                   # This documentation
```

## 🚀 Quick Start

### Local Development Setup

1. **Initialize Supabase project:**

   ```bash
   supabase init
   supabase start
   ```

2. **Apply the consolidated schema:**

   ```bash
   supabase db reset
   ```

3. **Load development data:**

   ```bash
   psql postgres://postgres:postgres@localhost:54322/postgres < supabase/seed.sql
   ```

### Production Deployment

1. **Link to production project:**

   ```bash
   supabase link --project-ref your-project-ref
   ```

2. **Deploy schema:**

   ```bash
   supabase db push
   ```

## 📊 Schema Overview

### Database Entity Relationships

```mermaid
erDiagram
    auth_users ||--o{ trips : owns
    auth_users ||--o{ chat_sessions : creates
    auth_users ||--o{ memories : has
    auth_users ||--o{ api_keys : manages
    
    trips ||--o{ flights : contains
    trips ||--o{ accommodations : includes
    trips ||--o{ transportation : uses
    trips ||--o{ itinerary_items : has
    trips ||--o{ chat_sessions : discusses
    
    chat_sessions ||--o{ chat_messages : contains
    chat_messages ||--o{ chat_tool_calls : triggers
    
    memories ||--o{ session_memories : creates
    
    auth_users {
        uuid id PK
        string email
        timestamp created_at
        timestamp updated_at
    }
    
    trips {
        uuid id PK
        uuid user_id FK
        string title
        text description
        date start_date
        date end_date
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }
    
    chat_sessions {
        uuid id PK
        uuid user_id FK
        uuid trip_id FK
        string title
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }
    
    memories {
        uuid id PK
        uuid user_id FK
        text content
        vector embedding
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }
    
    api_keys {
        uuid id PK
        uuid user_id FK
        string name
        text encrypted_key
        string provider
        timestamp created_at
        timestamp last_used_at
    }
```

### Core Business Tables

| Table | Description | Key Features |
|-------|-------------|--------------|
| `trips` | Travel itineraries | User-owned via `auth.users`, RLS enabled |
| `flights` | Flight options and bookings | Linked to trips, price tracking |
| `accommodations` | Hotel/lodging options | Rating system, amenity tracking |
| `transportation` | Ground transport options | Multi-modal transport support |
| `itinerary_items` | Detailed trip activities | Flexible activity planning |

### Chat & AI System

| Table | Description | Key Features |
|-------|-------------|--------------|
| `chat_sessions` | Conversation sessions | Trip-linked context |
| `chat_messages` | Individual messages | Role-based (user/assistant/system) |
| `chat_tool_calls` | AI tool invocations | Tool result tracking |

### Memory & Personalization

| Table | Description | Key Features |
|-------|-------------|--------------|
| `memories` | Long-term user preferences | pgvector embeddings, semantic search |
| `session_memories` | Conversation context | Temporary, auto-expiring |

### API Management

| Table | Description | Key Features |
|-------|-------------|--------------|
| `api_keys` | BYOK (Bring Your Own Keys) | Encrypted storage, usage tracking |

## 🔒 Security Features

### Row Level Security (RLS)

- **Multi-tenant isolation**: Users can only access their own data
- **Automatic enforcement**: Policies applied at database level
- **Supabase Auth integration**: Uses `auth.uid()` for user identification

### Key Security Policies

- Users own their trips and all related data
- Chat sessions are user-scoped
- API keys are private to each user
- Memory data is isolated by user

## 🔍 Key Features

### Vector Search & AI

- **pgvector integration**: Semantic search for memories
- **Embedding storage**: 1536-dimension vectors (OpenAI compatible)
- **Hybrid search**: Vector similarity + metadata filtering

### Performance Optimization

- **Strategic indexing**: B-tree indexes on frequently queried columns
- **Vector indexes**: IVFFlat indexes for embedding similarity
- **Maintenance functions**: Automated cleanup and optimization

### Data Integrity

- **Foreign key constraints**: Referential integrity enforcement
- **Check constraints**: Data validation at database level
- **Automated timestamps**: `updated_at` triggers

## 🛠️ Management Commands

### Database Maintenance

```sql
-- Run weekly for optimal performance
SELECT maintain_database_performance();

-- Clean up old memories (monthly)
SELECT cleanup_old_memories();

-- Expire inactive sessions (daily)
SELECT expire_inactive_sessions();
```

### Development Utilities

```bash
# Generate migration from schema changes
supabase db diff --file new_migration_name

# Pull remote schema changes
supabase db pull

# Reset local database
supabase db reset

# View migration status
supabase migration list
```

## 🧪 Testing

### Schema Tests

- Table creation verification
- RLS policy testing
- Function correctness validation
- Index performance benchmarks

### Integration Tests

- Authentication flow testing
- API key management
- Memory system functionality
- Chat session management

## 📈 Performance Characteristics

### Expected Performance

- **Vector search**: <100ms for semantic queries
- **Trip queries**: <50ms for user data retrieval
- **Chat sessions**: <25ms for message loading
- **API key operations**: <10ms for validation

### Optimization Features

- **Connection pooling**: Configured for high concurrency
- **Query optimization**: Proper index usage
- **Memory management**: Automatic cleanup functions
- **Vector indexing**: IVFFlat for efficient similarity search

## 🔄 Migration Strategy

### From Existing Systems

1. **Backup current data**: Use `pg_dump` for safety
2. **Apply consolidated migration**: Single deployment operation
3. **Verify data integrity**: Run built-in verification queries
4. **Test application integration**: Validate all functionality

### Future Schema Changes

1. **Update schema files**: Modify appropriate schema file
2. **Generate migration**: `supabase db diff --file change_name`
3. **Review migration**: Verify generated SQL
4. **Apply changes**: Deploy through CI/CD pipeline

## 🌍 Environment Configuration

### Required Environment Variables

```env
SUPABASE_URL=your-project-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
GOOGLE_CLIENT_ID=your-google-oauth-id
GITHUB_CLIENT_ID=your-github-oauth-id
```

### OAuth Configuration

- Configure providers in Supabase Dashboard
- Set redirect URLs for development and production
- Enable appropriate scopes for user data

## 📚 Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TripSage Architecture Guide](../docs/03_ARCHITECTURE/DATABASE_ARCHITECTURE.md)

## 🆘 Troubleshooting

### Common Issues

**Extension not found:**

```sql
-- Enable in Supabase Dashboard: Database > Extensions
CREATE EXTENSION IF NOT EXISTS vector;
```

**RLS blocking queries:**

```sql
-- Check auth context
SELECT auth.uid();

-- Temporarily disable for debugging (dev only!)
ALTER TABLE table_name DISABLE ROW LEVEL SECURITY;
```

**Vector index issues:**

```sql
-- Rebuild vector index
DROP INDEX IF EXISTS idx_memories_embedding;
CREATE INDEX idx_memories_embedding ON memories 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

---

**Schema Version**: Production v1.0  
**Last Updated**: 2025-06-09  
**Compatibility**: Supabase CLI v1.x, PostgreSQL 15+
