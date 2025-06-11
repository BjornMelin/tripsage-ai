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

### Automated Deployment (Recommended)

**For Local Development:**
```bash
# Run automated deployment with validation
python3 supabase/deploy_database_schema.py local
```

**For Production:**
```bash
# Deploy to production with project reference
python3 supabase/deploy_database_schema.py production --project-ref your-project-ref
```

### Manual Setup (Alternative)

**Local Development Setup:**

1. **Prerequisites:**
   ```bash
   # Install Supabase CLI
   npm install -g supabase
   
   # Verify installation
   supabase --version
   ```

2. **Initialize and validate:**
   ```bash
   # Validate schema before deployment
   python3 supabase/validate_database_schema.py
   
   # Start local Supabase
   supabase init
   supabase start
   ```

3. **Apply schema:**
   ```bash
   # Apply consolidated schema
   supabase db reset
   
   # Verify deployment
   python3 supabase/test_database_integration.py
   ```

4. **Load development data (optional):**
   ```bash
   psql postgres://postgres:postgres@localhost:54322/postgres < supabase/seed.sql
   ```

**Production Deployment:**

1. **Pre-deployment validation:**
   ```bash
   # Validate schema integrity
   python3 supabase/validate_database_schema.py
   
   # Run integration tests
   python3 supabase/test_database_integration.py
   ```

2. **Deploy to production:**
   ```bash
   # Link to production project
   supabase link --project-ref your-project-ref
   
   # Push schema
   supabase db push
   
   # Verify production deployment
   python3 supabase/test_database_integration.py
   ```

### Environment Setup

**Required Environment Variables:**
```bash
# Copy and configure environment
cp .env.example .env

# Edit .env with your Supabase credentials:
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
```

## 📊 Schema Overview

### Database Entity Relationships

```mermaid
erDiagram
    auth_users ||--o{ trips : owns
    auth_users ||--o{ trip_collaborators : collaborates
    auth_users ||--o{ chat_sessions : creates
    auth_users ||--o{ memories : has
    auth_users ||--o{ api_keys : manages
    
    trips ||--o{ trip_collaborators : "shared with"
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
        bigint id PK
        uuid user_id FK
        string name
        date start_date
        date end_date
        string destination
        numeric budget
        integer travelers
        string status
        string trip_type
        jsonb flexibility
        text[] notes
        jsonb search_metadata
        timestamp created_at
        timestamp updated_at
    }
    
    trip_collaborators {
        bigint id PK
        bigint trip_id FK
        uuid user_id FK
        string permission_level
        uuid added_by FK
        timestamp added_at
        timestamp updated_at
    }
    
    flights {
        bigint id PK
        bigint trip_id FK
        string origin
        string destination
        date departure_date
        date return_date
        string flight_class
        numeric price
        string currency
        string airline
        string booking_status
        string external_id
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }
    
    accommodations {
        bigint id PK
        bigint trip_id FK
        string name
        string address
        date check_in_date
        date check_out_date
        string room_type
        numeric price_per_night
        numeric total_price
        string currency
        numeric rating
        text[] amenities
        string booking_status
        string external_id
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }
    
    transportation {
        bigint id PK
        bigint trip_id FK
        string transport_type
        string origin
        string destination
        timestamp departure_time
        timestamp arrival_time
        numeric price
        string currency
        string booking_status
        string external_id
        jsonb metadata
        timestamp created_at
    }
    
    itinerary_items {
        bigint id PK
        bigint trip_id FK
        string title
        text description
        string item_type
        timestamp start_time
        timestamp end_time
        string location
        numeric price
        string currency
        string booking_status
        string external_id
        jsonb metadata
        timestamp created_at
    }
    
    chat_sessions {
        uuid id PK
        uuid user_id FK
        bigint trip_id FK
        timestamp created_at
        timestamp updated_at
        timestamp ended_at
        jsonb metadata
    }
    
    chat_messages {
        bigint id PK
        uuid session_id FK
        string role
        text content
        timestamp created_at
        jsonb metadata
    }
    
    chat_tool_calls {
        bigint id PK
        bigint message_id FK
        string tool_id
        string tool_name
        jsonb arguments
        jsonb result
        string status
        timestamp created_at
        timestamp completed_at
        text error_message
    }
    
    memories {
        bigint id PK
        string user_id
        string memory_type
        text content
        vector embedding
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }
    
    session_memories {
        bigint id PK
        uuid session_id FK
        string user_id
        text content
        vector embedding
        jsonb metadata
        timestamp created_at
    }
    
    api_keys {
        bigint id PK
        uuid user_id FK
        string service_name
        string key_name
        text encrypted_key
        string key_hash
        boolean is_active
        timestamp last_used_at
        timestamp expires_at
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }
```

### Core Business Tables

| Table | Description | Key Features |
|-------|-------------|--------------|
| `trips` | Travel itineraries and plans | User-owned via `auth.users`, RLS enabled, full collaborative access with permission inheritance |
| `trip_collaborators` | **Trip sharing and collaboration system** | Permission-based sharing (view/edit/admin), role management, audit trail |
| `flights` | Flight options and bookings | Linked to trips, price tracking, collaborative access with edit permissions |
| `accommodations` | Hotel and lodging options | Rating system, amenity tracking, collaborative booking with permission validation |
| `transportation` | Ground transport options | Multi-modal support, collaborative access, shared transportation planning |
| `itinerary_items` | Detailed trip activities and schedule | Flexible activity planning, collaborative editing, timeline management |

### Chat & AI System (Collaboration-Enhanced)

| Table | Description | Key Features |
|-------|-------------|--------------|
| `chat_sessions` | Conversation sessions with AI | Trip-linked context, collaborative access for shared trip discussions |
| `chat_messages` | Individual chat messages | Role-based (user/assistant/system), collaborative viewing for trip-related chats |
| `chat_tool_calls` | AI tool invocations and results | Tool result tracking, shared visibility for collaborative decision-making |

### Memory & Personalization

| Table | Description | Key Features |
|-------|-------------|--------------|
| `memories` | Long-term user preferences and history | pgvector embeddings, semantic search, user-private data |
| `session_memories` | Conversation context and temporary data | Session-scoped, auto-expiring, chat context preservation |

### API Management

| Table | Description | Key Features |
|-------|-------------|--------------|
| `api_keys` | BYOK (Bring Your Own Keys) | Encrypted storage, usage tracking, service-specific key management |

### Enhanced Trip Collaboration System

| Feature | Description | Implementation |
|---------|-------------|----------------|
| **Granular Permissions** | `view`, `edit`, `admin` permission levels | Database-enforced via comprehensive RLS policies |
| **Seamless Collaborative Access** | Users access shared trips transparently | Automatic inheritance through `trip_collaborators` junction table |
| **Owner-Controlled Sharing** | Trip owners manage all collaborator permissions | Dedicated INSERT/UPDATE/DELETE policies with ownership validation |
| **Complete Data Isolation** | Multi-tenant security with zero data leakage | RLS on all tables with user-scoped access patterns |
| **Permission Inheritance** | Collaboration extends to all trip-related data | Flights, accommodations, chat sessions inherit trip permissions |
| **Audit Trail** | Full collaboration activity tracking | Timestamps, permission changes, user activity monitoring |
| **Performance Optimization** | Efficient collaboration queries | Composite indexes and optimized permission lookup patterns |

**Advanced Collaboration Functions:**
- `get_user_accessible_trips(user_id, include_role)` - Get owned + shared trips with role information
- `check_trip_permission(user_id, trip_id, permission)` - Validate user access with permission hierarchy
- `get_trip_permission_details(user_id, trip_id)` - Detailed permission information and capabilities
- `get_collaboration_statistics()` - System-wide collaboration analytics
- `get_trip_activity_summary(trip_id, days_back)` - User activity tracking for trip collaborations
- `bulk_update_collaborator_permissions(trip_id, user_id, updates)` - Efficient bulk permission management
- `cleanup_orphaned_collaborators()` - Maintenance function for data integrity

## 🔒 Security Features

### Enhanced Row Level Security (RLS) with Collaboration

- **Multi-tenant isolation with collaboration support**: Users access owned data plus explicitly shared resources
- **Granular permission enforcement**: View/edit/admin permissions enforced at database level
- **Automatic policy application**: Comprehensive RLS policies with zero manual security checks required
- **Supabase Auth integration**: Seamless integration with `auth.uid()` for user identification
- **Performance-optimized security**: Efficient permission lookups with composite indexes

### Comprehensive Security Policies

- **Trip Ownership**: Users own their trips and control all collaboration permissions
- **Collaborative Access**: Shared trips accessible based on explicit permission grants (view/edit/admin)
- **Inheritance Security**: All trip-related data (flights, accommodations, chat) inherits trip permissions
- **Chat System Security**: Messages accessible to trip collaborators while maintaining user privacy
- **API Key Privacy**: API keys remain completely private to individual users
- **Memory Data Isolation**: User preferences and memories isolated at application level
- **Audit Trail Security**: All collaboration activities tracked with timestamps and user attribution

### Security Policy Details

| Resource Type | Owner Permissions | Collaborator Permissions | Security Implementation |
|---------------|-------------------|-------------------------|------------------------|
| **Trips** | Full CRUD access | View/Edit based on permission level | RLS with permission hierarchy validation |
| **Flights** | Full CRUD access | View (all), Edit/Delete (edit+ permission) | Inherited from trip collaboration |
| **Accommodations** | Full CRUD access | View (all), Edit/Delete (edit+ permission) | Inherited from trip collaboration |
| **Chat Sessions** | Full CRUD access | View (all), Create/Edit own sessions | Trip-scoped collaborative access |
| **Chat Messages** | Full CRUD access | View (all), Create/Edit own messages | Session-scoped with trip inheritance |
| **API Keys** | Full CRUD access | No access (private) | User-scoped isolation |
| **Collaborators** | Full management | View own collaboration status | Owner-controlled with audit trail |

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
