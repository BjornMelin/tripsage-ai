# TripSage Supabase Project

Supabase infrastructure for TripSage. Database migrations are the source of truth,
and database webhooks post signed HTTP events to Vercel Route Handlers.

## Project Structure

```text
supabase/
├── schemas/                    # Legacy reference SQL (do not apply directly)
│   ├── 00_extensions.sql      # PostgreSQL extensions
│   ├── 01_tables.sql          # Core table definitions
│   ├── 02_indexes.sql         # Performance indexes
│   ├── 03_functions.sql       # Stored procedures
│   ├── 04_triggers.sql        # Database triggers
│   ├── 05_policies.sql        # Row Level Security
│   └── README.md              # Schema documentation
├── migrations/                 # Version-controlled migrations
│   ├── 20250609_*.sql         # Production schema
│   ├── 20250611_*.sql         # Feature additions
│   └── README.md              # Migration guide
├── (removed) edge-functions/  # Legacy (replaced by DB → Vercel webhooks)
├── (removed) functions/       # Legacy (replaced by DB → Vercel webhooks)
├── storage/                   # Legacy storage SQL (superseded by migrations)
│   ├── buckets.sql           # Bucket definitions
│   ├── policies.sql          # Storage RLS
│   └── README.md             # Storage guide
├── config.toml               # Supabase CLI config
├── seed.sql                  # Development data
├── .env.example              # Environment template
└── TROUBLESHOOTING.md        # Common issues
```

## Documentation Index

| Component | Documentation | Purpose |
|-----------|--------------|----------|
| **Schemas** | [schemas/README.md](./schemas/README.md) | Declarative schema management guide |
| **Migrations** | [migrations/README.md](./migrations/README.md) | Database migration best practices |
| **Webhooks (DB→Vercel)** | [../docs/operators/supabase-webhooks.md](../docs/operators/supabase-webhooks.md) | Configure database webhooks |
| **Storage** | [storage/README.md](./storage/README.md) | File storage and management |
| **Functions** | [functions/README.md](./functions/README.md) | Edge function suite |
| **Troubleshooting** | [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | Common issues and solutions |

## Setup Guide

### Prerequisites

- [Supabase CLI](https://supabase.com/docs/guides/cli) installed
- [Docker](https://www.docker.com/) for local development
- Python 3.8+ for deployment scripts
- Node.js 18+ for Supabase CLI

### 1. Initial Setup

```bash
# Clone and navigate to project
cd supabase/

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Local Development (migrations are authoritative)

```bash
# Initialize Supabase
supabase init

# Start local Supabase stack
supabase start

# Apply database schema
supabase db reset --debug

# Run local Supabase stack and test migrations
supabase start
supabase db reset --debug
```

### 3. Production Deployment (CLI migrations)

```bash
# Link to production project
supabase link --project-ref your-project-ref

# Push database changes
supabase db push

# Webhooks use Postgres settings (GUCs). See docs/operators/supabase-webhooks.md
```

### Notes on legacy SQL

- The `schemas/` and `storage/` folders contain historical SQL. They are not applied
  by the CLI and are kept for reference only while we complete migration parity.
- All changes must be expressed as timestamped files under `supabase/migrations/`.

```bash
# Validate schema integrity
python3 validate_database_schema.py

# Deploy to local environment
python3 deploy_database_schema.py local

# Deploy to production with validation
python3 deploy_database_schema.py production --project-ref your-project-ref

# Run integration tests
python3 test_database_integration.py
```

## Configuration

### Environment Variables / Settings

See [.env.example](./.env.example) for a complete list. Key variables:

```bash
# Supabase Core
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Webhooks are configured via Postgres settings (GUCs). See docs/operators/supabase-webhooks.md.
# Example (set in DB):
# app.vercel_webhook_trips = 'https://<vercel>/api/hooks/trips'
# app.vercel_webhook_cache = 'https://<vercel>/api/hooks/cache'
# app.webhook_hmac_secret   = '<secret>'

# Storage
STORAGE_BUCKET=attachments
MAX_FILE_SIZE=50000000
```

### Database Connection

```bash
# Direct connection (for migrations)
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Pooled connection (for applications)
DATABASE_POOLER_URL=postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
```

## Database Architecture

### Components

1. **[Declarative Schemas](./schemas/README.md)** - Define database structure
   in SQL files
2. **[Migrations](./migrations/README.md)** - Version-controlled database changes
3. **Webhooks (DB→Vercel)** - Signed HTTP events to Vercel Route Handlers
4. **[Storage](./storage/README.md)** - File storage with RLS policies
5. **[Functions](./functions/README.md)** - Serverless suite

### Entity Relationship Diagram

```mermaid
erDiagram
    auth_users ||--o{ trips : owns
    auth_users ||--o{ trip_collaborators : collaborates
    auth_users ||--o{ chat_sessions : creates
    auth_users ||--o{ memories : has
    
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

| Table | Description | Details |
|-------|-------------|--------------|
| `trips` | Travel itineraries and plans | User-owned, RLS enabled, full collaborative access |
| `trip_collaborators` | Trip sharing and collaboration | Permission-based sharing (view/edit/admin), role management, audit trail |
| `flights` | Flight options and bookings | Linked to trips, price tracking, collaborative edit permissions |
| `accommodations` | Hotel and lodging options | Rating system, amenity tracking, collaborative booking permissions |
| `transportation` | Ground transport options | Multi-modal support, collaborative access, shared planning |
| `itinerary_items` | Trip activities and schedule | Flexible planning, collaborative editing, timeline management |

### Chat & AI System (Collaboration Suite)

| Table | Description | Details |
|-------|-------------|--------------|
| `chat_sessions` | AI conversation sessions | Trip-linked context, collaborative access for discussions |
| `chat_messages` | Individual chat messages | Role-based (user/assistant/system), collaborative viewing |
| `chat_tool_calls` | AI tool invocations and results | Tool result tracking, shared visibility for decisions |

### Memory & Personalization

| Table | Description | Details |
|-------|-------------|--------------|
| `memories` | Long-term user preferences and history | pgvector embeddings, semantic search, user-private data |
| `session_memories` | Conversation context and temporary data | Session-scoped, auto-expiring, chat context preservation |

### API Management

| Table | Description | Details |
|-------|-------------|--------------|

### Trip Collaboration System

| Feature | Description | Implementation |
|---------|-------------|----------------|
| **Granular Permissions** | `view`, `edit`, `admin` permission levels | Database-enforced via RLS policies |
| **Seamless Collaborative Access** | Users access shared trips transparently | Automatic inheritance through trip_collaborators junction table |
| **Owner-Controlled Sharing** | Trip owners manage collaborator permissions | Dedicated INSERT/UPDATE/DELETE policies with ownership validation |
| **Complete Data Isolation** | Multi-tenant security, zero data leakage | RLS on all tables with user-scoped access patterns |
| **Permission Inheritance** | Collaboration extends to trip-related data | Flights, accommodations, chat sessions inherit trip permissions |
| **Audit Trail** | Collaboration activity tracking | Timestamps, permission changes, user activity monitoring |
| **Performance** | Efficient collaboration queries | Composite indexes and optimized permission lookups |

**Collaboration Functions:**

- `get_user_accessible_trips(user_id, include_role)` - Get owned + shared trips with role information
- `check_trip_permission(user_id, trip_id, permission)` - Validate user access  with permission hierarchy
- `get_trip_permission_details(user_id, trip_id)` - Detailed permission  information and capabilities
- `get_collaboration_statistics()` - System-wide collaboration analytics
- `get_trip_activity_summary(trip_id, days_back)` - User activity tracking  for trip collaborations
- `bulk_update_collaborator_permissions(trip_id, user_id, updates)` - Efficient  bulk permission management
- `cleanup_orphaned_collaborators()` - Maintenance function for data integrity

## Security

### Row Level Security (RLS) with Collaboration

- **Multi-tenant isolation with collaboration support**: Users access owned data  plus explicitly shared resources
- **Granular permission enforcement**: View/edit/admin permissions enforced at database level
- **Automatic policy application**: RLS policies with zero manual  security checks required
- **Supabase Auth integration**: Seamless integration with `auth.uid()` for user identification
- **Performance-optimized security**: Efficient permission lookups with composite indexes

### Security Policies

- **Trip Ownership**: Users own their trips and control all collaboration permissions
- **Collaborative Access**: Shared trips accessible based on explicit  permission grants (view/edit/admin)
- **Inheritance Security**: All trip-related data (flights, accommodations,  chat) inherits trip permissions
- **Chat System Security**: Messages accessible to trip collaborators while maintaining user privacy
- **API Key Privacy**: API keys remain completely private to individual users
- **Memory Data Isolation**: User preferences and memories isolated at application level
- **Audit Trail Security**: All collaboration activities tracked with  timestamps and user attribution

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

## Features

### Vector Search & AI

- **pgvector integration**: Semantic search for memories
- **Embedding storage**: 1536-dimension vectors (OpenAI compatible)
- **Hybrid search**: Vector similarity + metadata filtering

### Performance Details

- **Strategic indexing**: B-tree indexes on frequently queried columns
- **Vector indexes**: IVFFlat indexes for embedding similarity
- **Maintenance functions**: Automated cleanup and optimization

### Data Integrity

- **Foreign key constraints**: Referential integrity enforcement
- **Check constraints**: Data validation at database level
- **Automated timestamps**: `updated_at` triggers

## Management Commands

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
supabase db reset --debug

# View migration status
supabase migration list
```

## Testing

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

## Performance

### Expected Performance

- **Vector search**: <100ms for semantic queries
- **Trip queries**: <50ms for user data retrieval
- **Chat sessions**: <25ms for message loading
- **API key operations**: <10ms for validation

### System Features

- **Connection pooling**: Configured for high concurrency
- **Query optimization**: Proper index usage
- **Memory management**: Automatic cleanup functions
- **Vector indexing**: IVFFlat for efficient similarity search

## Migration Strategy

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

## Environment Configuration

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

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TripSage Architecture Guide](../docs/03_ARCHITECTURE/DATABASE_ARCHITECTURE.md)

## Testing & Validation

### Schema Validation

```bash
# Validate schema files
python3 validate_database_schema.py

# Test migrations locally
supabase db reset --debug --debug
```

### Integration Testing

```bash
# Run full test suite
python3 test_database_integration.py

# Test edge functions
deno task test
```

### Performance Testing

```sql
-- Check query performance
EXPLAIN ANALYZE SELECT * FROM trips WHERE user_id = 'uuid';

-- Monitor index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## Monitoring & Maintenance

### Health Checks

```sql
-- Database size
SELECT pg_database_size(current_database()) / 1024 / 1024 as size_mb;

-- Table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Active connections
SELECT count(*) FROM pg_stat_activity;
```

### Regular Maintenance

```bash
# Weekly tasks
- Review slow query logs
- Check index usage statistics
- Monitor storage usage
- Review error logs

# Monthly tasks
- Analyze table statistics
- Review and optimize queries
- Check for unused indexes
- Update dependencies
```

## Security Practices

1. **Always use RLS** - Enable on all tables
2. **Secure functions** - Use `SECURITY DEFINER` carefully
3. **Validate inputs** - Sanitize all user inputs
4. **Use service role sparingly** - Only for admin operations
5. **Monitor access logs** - Regular security audits

## Deployment Checklist

### Pre-deployment

- [ ] All tests passing
- [ ] Schema validated
- [ ] Migrations reviewed
- [ ] Environment variables set
- [ ] Backup created

### Deployment

- [ ] Link to correct project
- [ ] Push migrations
- [ ] Deploy functions
- [ ] Set secrets
- [ ] Verify deployment

### Post-deployment

- [ ] Run integration tests
- [ ] Check logs for errors
- [ ] Monitor performance
- [ ] Update documentation

## Additional Resources - Documentation

### Internal Documentation

- [Database Architecture](../docs/03_ARCHITECTURE/DATABASE_ARCHITECTURE.md)
- [API Documentation](../docs/API.md)
- [Security Guide](../docs/SECURITY.md)

### External Resources

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Deno Documentation](https://deno.land/manual)
- [pgvector Documentation](https://github.com/pgvector/pgvector)

## Contributing

### Making Changes

1. Create feature branch
2. Update schema files
3. Generate migrations
4. Add tests
5. Update documentation
6. Submit pull request

### Code Standards

- SQL files use 2-space indentation
- Functions follow naming convention: `verb_noun_object`
- Tables use snake_case
- Always include comments

## Getting Help

- **Common Issues**: See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **Schema Questions**: Check [schemas/README.md](./schemas/README.md)
- **Migration Help**: See [migrations/README.md](./migrations/README.md)
- **Function Issues**: Check [functions/README.md](./functions/README.md)

---

**Version**: 2.1.0
**Last Updated**: 2025-11-13
**Maintained By**: TripSage Development Team
