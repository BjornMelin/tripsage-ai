# TripSage Supabase Configuration

Complete setup guide for TripSage's Supabase infrastructure, including database schema, security policies, edge functions, and deployment procedures.

## Prerequisites

### Development Tools

For local development and troubleshooting:

```bash
# Install Supabase CLI (for local dev and troubleshooting)
npm install -g supabase
supabase --version

# Install dependencies
pnpm add @supabase/supabase-js
uv add supabase python-dotenv  # or: pip install supabase python-dotenv
```

### Account Setup

- **Supabase Account**: Pro plan required for pgvector extension
- **Vercel Account**: For automated deployment and management
- **Domain**: For production deployment (managed through Vercel)

## Project Setup

### Create Project

1. Navigate to [Supabase Dashboard](https://supabase.com/dashboard)
2. Click "New Project"
3. Configure:
   - **Name**: `tripsage-production`
   - **Database Password**: Use strong, generated password
   - **Region**: Choose closest to your users
   - **Plan**: Pro or Enterprise (required for pgvector)

### Enable Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_cron";
CREATE EXTENSION IF NOT EXISTS "pg_net";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
```

### Verify Extensions

```sql
SELECT extname as extension_name, extversion as version
FROM pg_extension
WHERE extname IN ('uuid-ossp', 'vector', 'pg_cron', 'pg_net', 'pgcrypto', 'pg_stat_statements', 'btree_gist')
ORDER BY extname;
```

## Environment Configuration

### Production Variables

Create `.env.production`:

```bash
# Supabase
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>

# Database
SUPABASE_TIMEOUT=30
SUPABASE_POOL_SIZE=20
SUPABASE_MAX_OVERFLOW=30

# Security
SECRET_KEY=<strong-production-secret-key>
CORS_ORIGINS=https://your-domain.com
ALLOWED_HOSTS=your-domain.com,api.your-domain.com

# Monitoring
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=<your-sentry-dsn>
```

### Frontend Variables

Create `frontend/.env.production`:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
NEXTAUTH_URL=https://your-domain.com
NEXTAUTH_SECRET=<your-nextauth-secret>
```

## Database Schema and Migrations

### Local Development Setup

```bash
# Initialize Supabase locally
supabase init

# Link to production project
supabase link --project-ref <your-project-ref>

# Apply schema changes
supabase db push
```

### Migration Management

```bash
# Create new migration
supabase migration new descriptive_migration_name

# Apply migrations
supabase db push

# Check migration status
supabase migration list

# Reset local database
supabase db reset
```

### Schema Verification

```sql
-- Check table creation
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Verify RLS is enabled
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public' AND rowsecurity = true;
```

## Security Configuration

### Row Level Security (RLS)

Enable RLS on all tables and create appropriate policies:

```sql
-- Enable RLS on core tables
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_collaborators ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
```

### Core Security Policies

```sql
-- Trip access policies
CREATE POLICY "Users can view their own trips"
ON trips FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can view shared trips"
ON trips FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM trip_collaborators tc
    WHERE tc.trip_id = trips.id
    AND tc.user_id = auth.uid()
    AND tc.permission IN ('read', 'write', 'admin')
  )
);

-- Memory access policies
CREATE POLICY "Users can view their own memories"
ON memories FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own memories"
ON memories FOR INSERT
WITH CHECK (auth.uid() = user_id);
```

### Authentication Setup

Configure auth settings in Supabase Dashboard:

1. Navigate to Authentication > Settings
2. Configure:
   - Site URL: `https://your-production-domain.com`
   - Additional redirect URLs: `https://your-staging-domain.com`, `http://localhost:3000`
   - JWT expiry: 3600 seconds
   - Enable refresh token rotation

## Edge Functions

### Available Functions

- `ai-processing`: Handles AI chat completions and memory processing
- `trip-events`: Processes trip collaboration notifications

### Local Development

```bash
# Serve functions locally
supabase functions serve

# Serve specific function
supabase functions serve ai-processing --no-verify-jwt
```

### Function Deployment

```bash
# Deploy all functions
supabase functions deploy

# Deploy specific function
supabase functions deploy ai-processing

# Set environment variables
supabase secrets set OPENAI_API_KEY=your_key
supabase secrets set RESEND_API_KEY=your_key
```

### Monitoring Functions

```bash
# View function logs
supabase functions logs ai-processing --tail

# Check function status
supabase functions logs ai-processing --limit 100
```

## Real-time Configuration

### Enable Real-time

```sql
-- Create real-time publication
DROP PUBLICATION IF EXISTS supabase_realtime CASCADE;
CREATE PUBLICATION supabase_realtime;

-- Add tables to real-time publication
ALTER PUBLICATION supabase_realtime ADD TABLE trips;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE trip_collaborators;
```

### Real-time Policies

```sql
-- Real-time access policies
CREATE POLICY "Real-time trip access"
ON trips FOR SELECT
USING (
  auth.uid() = user_id OR
  EXISTS (
    SELECT 1 FROM trip_collaborators tc
    WHERE tc.trip_id = trips.id
    AND tc.user_id = auth.uid()
  )
);
```

## Performance Optimization

### Database Indexes

```sql
-- Vector search indexes
CREATE INDEX memories_embedding_hnsw_idx ON memories
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- User-specific indexes
CREATE INDEX idx_trips_user_id ON trips(user_id);
CREATE INDEX idx_chat_sessions_trip_id ON chat_sessions(trip_id);

-- Composite indexes
CREATE INDEX idx_trips_user_date ON trips(user_id, start_date);
```

### Connection Pooling

```bash
# Production settings
SUPABASE_POOL_SIZE=20
SUPABASE_MAX_OVERFLOW=30
SUPABASE_POOL_TIMEOUT=30
SUPABASE_POOL_RECYCLE=3600
```

### Query Monitoring

```sql
-- Enable query statistics
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = 10000;
SELECT pg_reload_conf();

-- Monitor slow queries
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC
LIMIT 20;
```

## Troubleshooting

> **Note**: For manual CLI operation issues and emergency procedures, see [Manual Supabase Operations](supabase-manual-operations.md).

### Connection Issues

**Cannot connect to Supabase:**

```bash
# Check environment variables
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY

# Test API endpoint
curl -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  $SUPABASE_URL/rest/v1/
```

**Database connection pool exhausted:**

```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- View connection details
SELECT pid, usename, application_name, state
FROM pg_stat_activity
WHERE state = 'active';
```

### Migration Problems

**Migration fails to apply:**

```bash
# Check migration status
supabase migration list

# Fix permission issues
supabase db reset
```

**RLS policy issues:**

```sql
-- Debug RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

### Edge Function Errors

**Function deployment fails:**

```bash
# Check function status
supabase functions logs function-name --tail

# Verify secrets are set
supabase secrets list
```

### Performance Issues

**Slow queries:**

```sql
-- Find slow queries
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC
LIMIT 20;
```

**High connection count:**

```sql
-- Monitor connections
SELECT state, count(*) as connections
FROM pg_stat_activity
WHERE pid <> pg_backend_pid()
GROUP BY state;
```

## Deployment

Supabase infrastructure is automatically deployed and managed through Vercel Supabase integration. Schema migrations and edge functions are deployed as part of the Vercel deployment process.

### Deployment Process

1. **Schema Migrations**: Applied automatically during Vercel builds
2. **Edge Functions**: Deployed through Vercel's Supabase integration
3. **Environment Variables**: Managed through Vercel environment variables
4. **Secrets**: Configured through Vercel Supabase integration

For deployment details, see the [Vercel deployment documentation](../operators/deployment-guide.md).

### Manual Operations

For manual Supabase operations (rarely needed):

```bash
# Link to project (one-time)
supabase link --project-ref your-project-ref

# Check deployment status
supabase status

# View function logs
supabase functions logs function-name --tail
```

## References

- [Supabase Documentation](https://supabase.com/docs)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TripSage Database Architecture](../docs/03_ARCHITECTURE/DATABASE_ARCHITECTURE.md)

---

**Last Updated:** 2025-11-02
