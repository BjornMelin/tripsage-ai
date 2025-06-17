# Supabase Production Setup Guide

This comprehensive guide covers the complete setup and deployment of TripSage on Supabase for production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Supabase Project Setup](#supabase-project-setup)
- [Database Schema Deployment](#database-schema-deployment)
- [Security Configuration](#security-configuration)
- [Environment Configuration](#environment-configuration)
- [Real-time Setup](#real-time-setup)
- [Performance Optimization](#performance-optimization)
- [Monitoring & Alerting](#monitoring--alerting)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

```bash
# Install Supabase CLI
npm install -g supabase

# Verify installation
supabase --version

# Install required dependencies
npm install @supabase/supabase-js
pip install supabase python-dotenv
```

### Account Requirements

- **Supabase Account**: Pro plan or higher (required for pgvector and advanced features)
- **GitHub Account**: For CI/CD automation
- **Domain**: For production deployment with custom URLs

### Plan Requirements

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| pgvector Extension | ❌ | ✅ | ✅ |
| Real-time Subscriptions | Limited | ✅ | ✅ |
| Row Level Security | ✅ | ✅ | ✅ |
| Custom Domains | ❌ | ✅ | ✅ |
| Advanced Monitoring | ❌ | ✅ | ✅ |
| SLA | None | 99.9% | 99.99% |

## Supabase Project Setup

### 1. Create Production Project

```bash
# Login to Supabase
supabase login

# Create new project via CLI (or use dashboard)
# Note: Project creation via CLI requires organization setup
```

**Via Supabase Dashboard:**

1. Navigate to [Supabase Dashboard](https://supabase.com/dashboard)
2. Click "New Project"
3. Select your organization
4. Configure project:
   - **Name**: `tripsage-production`
   - **Database Password**: Use strong, generated password
   - **Region**: Choose closest to your users
   - **Plan**: Pro or Enterprise (required for pgvector)

### 2. Enable Required Extensions

```sql
-- Connect to your project SQL editor
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_cron";
CREATE EXTENSION IF NOT EXISTS "pg_net";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
```

### 3. Verify Extension Installation

```sql
-- Check installed extensions
SELECT 
    extname as extension_name,
    extversion as version
FROM pg_extension 
WHERE extname IN (
    'uuid-ossp', 'vector', 'pg_cron', 'pg_net', 
    'pgcrypto', 'pg_stat_statements', 'btree_gist'
)
ORDER BY extname;
```

## Database Schema Deployment

### 1. Initialize Local Development

```bash
# Clone your repository
git clone <your-repo-url>
cd tripsage

# Initialize Supabase locally
supabase init

# Link to your production project
supabase link --project-ref <your-project-ref>
# Get project ref from: https://supabase.com/dashboard/project/<project-ref>
```

### 2. Deploy Database Schema

```bash
# Push all schema changes to production
supabase db push

# Verify deployment
supabase db diff
```

#### Alternative: Deploy via Schema Files

```bash
# If using schema files approach
cd supabase

# Execute schema files in order
psql -d "$DATABASE_URL" -f schemas/00_extensions.sql
psql -d "$DATABASE_URL" -f schemas/01_tables.sql
psql -d "$DATABASE_URL" -f schemas/02_indexes.sql
psql -d "$DATABASE_URL" -f schemas/03_functions.sql
psql -d "$DATABASE_URL" -f schemas/04_triggers.sql
psql -d "$DATABASE_URL" -f schemas/05_policies.sql
psql -d "$DATABASE_URL" -f schemas/06_views.sql
```

### 3. Verify Schema Deployment

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

-- Check vector extension tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_name LIKE '%memor%' OR table_name LIKE '%vector%';
```

## Security Configuration

### 1. Row Level Security Setup

**Enable RLS on All Tables:**

```sql
-- Enable RLS on core tables
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_collaborators ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE itinerary_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_notes ENABLE ROW LEVEL SECURITY;
```

**Create Security Policies:**

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

CREATE POLICY "Users can modify their own trips"
ON trips FOR UPDATE
USING (auth.uid() = user_id);

CREATE POLICY "Collaborators can modify shared trips"
ON trips FOR UPDATE
USING (
  EXISTS (
    SELECT 1 FROM trip_collaborators tc
    WHERE tc.trip_id = trips.id 
    AND tc.user_id = auth.uid()
    AND tc.permission IN ('write', 'admin')
  )
);

-- Memory access policies
CREATE POLICY "Users can view their own memories"
ON memories FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own memories"
ON memories FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- API key access policies
CREATE POLICY "Users can manage their own API keys"
ON api_keys FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);
```

### 2. Authentication Configuration

**Configure Auth Settings:**

1. Navigate to Authentication > Settings in Supabase Dashboard
2. Configure the following:

```json
{
  "site_url": "https://your-production-domain.com",
  "additional_redirect_urls": [
    "https://your-staging-domain.com",
    "http://localhost:3000"
  ],
  "jwt_expiry": 3600,
  "refresh_token_rotation_enabled": true,
  "security_update_password_require_reauthentication": true
}
```

**Email Templates:**

1. Customize email templates in Authentication > Email Templates
2. Configure SMTP settings for production email delivery
3. Set up custom domain for emails (optional but recommended)

### 3. API Security

**Configure API Settings:**

```bash
# Set environment variables
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>  # Keep secret, server-side only
SUPABASE_ANON_KEY=<anon-key>  # Public key for client-side
```

**API Key Management:**

```sql
-- Create function to rotate API keys (if needed)
CREATE OR REPLACE FUNCTION rotate_user_api_key(
    p_user_id UUID,
    p_service TEXT
) RETURNS TEXT AS $$
DECLARE
    new_key TEXT;
BEGIN
    -- Generate new encrypted key
    new_key := encode(gen_random_bytes(32), 'base64');
    
    -- Update existing key
    UPDATE api_keys 
    SET 
        encrypted_key = crypt(new_key, gen_salt('bf')),
        updated_at = NOW()
    WHERE user_id = p_user_id AND service = p_service;
    
    RETURN new_key;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

## Environment Configuration

### 1. Production Environment Variables

Create `.env.production`:

```bash
# Environment
ENVIRONMENT=production
DEBUG=false

# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>

# Database Configuration
SUPABASE_TIMEOUT=30
SUPABASE_POOL_SIZE=20
SUPABASE_MAX_OVERFLOW=30

# DragonflyDB Cache (Production)
DRAGONFLY_URL=rediss://username:password@your-dragonfly-host:6380/0

# Security
SECRET_KEY=<strong-production-secret-key>
CORS_ORIGINS=https://your-domain.com
ALLOWED_HOSTS=your-domain.com,api.your-domain.com

# SSL/TLS
SSL_REDIRECT=true
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https

# Monitoring
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=<your-sentry-dsn>
PROMETHEUS_ENABLED=true

# Memory System
MEM0_API_KEY=<your-mem0-api-key>
MEMORY_VECTOR_STORE=supabase
VECTOR_DIMENSION=1536
```

### 2. Frontend Environment Variables

Create `frontend/.env.production`:

```bash
# Frontend Configuration
NEXT_PUBLIC_API_URL=https://api.your-domain.com
NEXT_PUBLIC_WS_URL=wss://api.your-domain.com/ws
NEXT_PUBLIC_ENVIRONMENT=production

# Supabase Frontend
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>

# Authentication
NEXTAUTH_URL=https://your-domain.com
NEXTAUTH_SECRET=<your-nextauth-secret>
```

### 3. Staging Environment Setup

For staging environment, create separate Supabase project and configure:

```bash
# Staging-specific variables
SUPABASE_URL=https://your-staging-project-ref.supabase.co
ENVIRONMENT=staging
DEBUG=false
```

## Real-time Setup

### 1. Enable Real-time Features

```sql
-- Create real-time publication
DROP PUBLICATION IF EXISTS supabase_realtime CASCADE;
CREATE PUBLICATION supabase_realtime;

-- Add tables to real-time publication
ALTER PUBLICATION supabase_realtime ADD TABLE trips;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE trip_collaborators;
ALTER PUBLICATION supabase_realtime ADD TABLE itinerary_items;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_tool_calls;
```

### 2. Configure Real-time Policies

```sql
-- Real-time policies for trips
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

-- Real-time policies for chat
CREATE POLICY "Real-time chat access"
ON chat_messages FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM chat_sessions cs
    WHERE cs.id = chat_messages.session_id
    AND cs.user_id = auth.uid()
  )
);
```

### 3. Test Real-time Functionality

```javascript
// Frontend real-time test
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
)

// Test real-time subscription
const subscription = supabase
  .channel('trips-changes')
  .on(
    'postgres_changes',
    {
      event: '*',
      schema: 'public',
      table: 'trips'
    },
    (payload) => {
      console.log('Trip change:', payload)
    }
  )
  .subscribe()
```

## Performance Optimization

### 1. Database Performance

**Vector Search Optimization:**

```sql
-- Optimize vector indexes for production workload
CREATE INDEX memories_embedding_hnsw_idx ON memories 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- User-specific vector index
CREATE INDEX memories_user_embedding_idx ON memories 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64)
WHERE user_id IS NOT NULL;

-- Analyze tables for query optimization
ANALYZE memories;
ANALYZE trips;
ANALYZE chat_messages;
```

**Connection Pool Configuration:**

```bash
# Production connection pool settings
SUPABASE_POOL_SIZE=20
SUPABASE_MAX_OVERFLOW=30
SUPABASE_POOL_TIMEOUT=30
SUPABASE_POOL_RECYCLE=3600  # 1 hour
```

### 2. Cache Configuration

**DragonflyDB Setup:**

```bash
# Production DragonflyDB configuration
DRAGONFLY_URL=rediss://username:password@your-host:6380/0
DRAGONFLY_POOL_SIZE=20
DRAGONFLY_TIMEOUT=5
DRAGONFLY_MAX_CONNECTIONS=100

# Multi-tier TTL strategy
CACHE_HOT_TTL=300       # 5 minutes
CACHE_WARM_TTL=3600     # 1 hour
CACHE_COLD_TTL=86400    # 24 hours
```

### 3. Query Performance Monitoring

```sql
-- Enable query monitoring
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = 10000;
SELECT pg_reload_conf();

-- Query to find slow queries
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    stddev_exec_time,
    max_exec_time
FROM pg_stat_statements 
WHERE mean_exec_time > 100  -- queries > 100ms
ORDER BY mean_exec_time DESC 
LIMIT 20;
```

## Monitoring & Alerting

### 1. Health Check Endpoints

Create comprehensive health checks:

```python
# Backend health check implementation
@app.get("/health/detailed")
async def detailed_health_check():
    checks = {
        "database": await check_database_health(),
        "cache": await check_cache_health(),
        "memory_system": await check_memory_system_health(),
        "real_time": await check_realtime_health(),
        "external_apis": await check_external_apis_health()
    }
    
    overall_status = "healthy" if all(
        check["status"] == "healthy" for check in checks.values()
    ) else "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "version": app.version
    }
```

### 2. Supabase Dashboard Monitoring

Configure alerts in Supabase Dashboard:

1. **Database Metrics**: Connection count, query performance, storage usage
2. **Authentication**: Failed login attempts, user registration rates
3. **Real-time**: Connection count, message throughput
4. **API Usage**: Request rates, error rates, response times

### 3. External Monitoring Setup

**Prometheus Metrics:**

```python
# Custom metrics for monitoring
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration'
)

# Database metrics
DB_CONNECTIONS = Gauge(
    'database_connections_active',
    'Active database connections'
)

VECTOR_SEARCH_DURATION = Histogram(
    'vector_search_duration_seconds',
    'Vector search query duration'
)
```

**Grafana Dashboard Configuration:**

```json
{
  "dashboard": {
    "title": "TripSage Production Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Database Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_activity_count",
            "legendFormat": "Active Connections"
          }
        ]
      },
      {
        "title": "Vector Search Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "vector_search_duration_seconds",
            "legendFormat": "Search Duration"
          }
        ]
      }
    ]
  }
}
```

## CI/CD Integration

### 1. GitHub Actions Workflow

Create `.github/workflows/deploy-production.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    env:
      SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
      SUPABASE_DB_PASSWORD: ${{ secrets.PRODUCTION_DB_PASSWORD }}
      SUPABASE_PROJECT_ID: ${{ secrets.PRODUCTION_PROJECT_ID }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Supabase CLI
        uses: supabase/setup-cli@v1
        with:
          version: latest

      - name: Link Supabase project
        run: supabase link --project-ref $SUPABASE_PROJECT_ID

      - name: Deploy database migrations
        run: supabase db push

      - name: Deploy Edge Functions
        run: supabase functions deploy

      - name: Run post-deployment tests
        run: |
          npm install
          npm run test:production

      - name: Notify deployment status
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### 2. Deployment Verification

```bash
# Post-deployment verification script
#!/bin/bash

echo "🚀 Verifying production deployment..."

# Check API health
curl -f https://api.your-domain.com/health || exit 1

# Check database connectivity
curl -f https://api.your-domain.com/health/database || exit 1

# Check real-time functionality
curl -f https://api.your-domain.com/health/realtime || exit 1

# Run basic smoke tests
npm run test:smoke

echo "✅ Production deployment verified successfully!"
```

### 3. Rollback Procedures

```yaml
# Rollback workflow
name: Rollback Production

on:
  workflow_dispatch:
    inputs:
      migration_version:
        description: 'Migration version to rollback to'
        required: true

jobs:
  rollback:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Supabase CLI
        uses: supabase/setup-cli@v1

      - name: Link Supabase project
        run: supabase link --project-ref ${{ secrets.PRODUCTION_PROJECT_ID }}

      - name: Rollback migrations
        run: supabase db reset --version ${{ github.event.inputs.migration_version }}

      - name: Verify rollback
        run: npm run test:production
```

## Troubleshooting

### 1. Common Issues

**Extension Installation Failed:**

```sql
-- Check extension availability
SELECT name, installed_version, default_version 
FROM pg_available_extensions 
WHERE name IN ('vector', 'pg_cron', 'pg_net');

-- Install extensions manually if needed
CREATE EXTENSION IF NOT EXISTS vector CASCADE;
```

**RLS Policy Issues:**

```sql
-- Debug RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies 
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- Test policy as specific user
SET ROLE authenticated;
SET request.jwt.claims.sub TO '<user-uuid>';
SELECT * FROM trips LIMIT 1;
RESET ROLE;
```

**Performance Issues:**

```sql
-- Check slow queries
SELECT 
    substring(query, 1, 100) as short_query,
    calls,
    total_exec_time,
    mean_exec_time
FROM pg_stat_statements 
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC;

-- Analyze table statistics
SELECT 
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables;
```

### 2. Debug Commands

```bash
# Check Supabase project status
supabase status

# View recent migrations
supabase migration list

# Generate schema diff
supabase db diff

# Check real-time connections
curl -H "Authorization: Bearer <service-role-key>" \
  "https://<project-ref>.supabase.co/rest/v1/rpc/realtime_connections"
```

### 3. Performance Monitoring Queries

```sql
-- Vector search performance
SELECT 
    COUNT(*) as search_count,
    AVG(extract(epoch from (clock_timestamp() - query_start))) as avg_duration
FROM pg_stat_activity 
WHERE query LIKE '%vector%' AND state = 'active';

-- Cache hit ratio
SELECT 
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio
FROM pg_statio_user_tables;

-- Connection analysis
SELECT 
    state,
    count(*) as connections
FROM pg_stat_activity 
WHERE pid <> pg_backend_pid()
GROUP BY state;
```

## Security Checklist

### Pre-Production Security Audit

- [ ] **RLS Enabled**: All user tables have RLS enabled
- [ ] **Policies Tested**: All RLS policies tested with different user roles
- [ ] **API Keys Secured**: Service role key never exposed to client-side
- [ ] **Environment Separation**: Production secrets isolated from development
- [ ] **HTTPS Enforced**: All connections use HTTPS/WSS
- [ ] **Auth Configured**: Production authentication settings configured
- [ ] **Monitoring Setup**: Security monitoring and alerting configured
- [ ] **Backup Strategy**: Automated backups configured and tested
- [ ] **Access Controls**: Database access restricted to application servers
- [ ] **Audit Logging**: Comprehensive audit logging enabled

### Post-Deployment Verification

- [ ] **Health Checks Pass**: All health endpoints returning healthy status
- [ ] **Real-time Working**: Real-time subscriptions functioning correctly
- [ ] **Performance Metrics**: Performance targets being met
- [ ] **Error Rates**: Error rates within acceptable thresholds
- [ ] **Security Scans**: Security vulnerability scans passed
- [ ] **Load Testing**: Application handles expected traffic load
- [ ] **Monitoring Active**: All monitoring and alerting systems active
- [ ] **Documentation Updated**: All documentation reflects production setup

---

## Conclusion

This comprehensive guide provides everything needed to deploy TripSage on Supabase in a production environment. The setup includes enterprise-grade security, performance optimization, monitoring, and automation.

For additional support:

- **Supabase Documentation**: [https://supabase.com/docs](https://supabase.com/docs)
- **TripSage Support**: Contact your technical lead
- **Emergency Procedures**: See [Incident Response Guide](../08_USER_GUIDES/INCIDENT_RESPONSE.md)

Remember to regularly review and update your production configuration as your application scales and evolves.
