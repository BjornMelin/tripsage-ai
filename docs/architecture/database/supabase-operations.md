# Supabase Operations & Webhooks

> **Target Audience**: DevOps engineers, backend developers, integration leads

This document describes Supabase operational patterns, webhook configurations, real-time features, and database operations for TripSage.

## Table of Contents

- [Webhook Architecture](#webhook-architecture)
- [Realtime Operations](#realtime-operations)
- [Database Monitoring](#database-monitoring)
- [Operational Procedures](#operational-procedures)

## Webhook Architecture

### Database-to-Vercel Integration

Supabase webhooks enable real-time synchronization between database changes and application logic:

```sql
-- supabase/migrations/20251113034500_webhooks_consolidated.sql
-- Install SECURITY DEFINER triggers that call supabase_functions.http_request
CREATE TRIGGER trips_webhook_trigger
  AFTER INSERT OR UPDATE OR DELETE ON trips
  FOR EACH ROW EXECUTE FUNCTION
    supabase_functions.http_request(
      'https://your-app.vercel.app/api/hooks/trips',
      'POST',
      json_build_object('event', 'trip_changed', 'data', row_to_json(NEW))::text,
      json_build_object('x-webhook-signature', sign_payload(row_to_json(NEW)::text))::text
    );
```

### Webhook Route Handlers

All webhook receivers are server-only Vercel Route Handlers:

```typescript
// src/app/api/hooks/trips/route.ts
import "server-only";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  // 1. Verify HMAC signature
  const signature = request.headers.get('x-webhook-signature');
  const body = await request.text();

  const isValid = await verifyWebhookSignature(body, signature);
  if (!isValid) {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 401 });
  }

  // 2. Deduplicate events using Upstash Redis
  const eventId = await getEventId(body);
  const processed = await checkIdempotency(eventId);
  if (processed) {
    return NextResponse.json({ ok: true }); // Already processed
  }

  // 3. Process webhook
  const payload = JSON.parse(body);
  await processTripWebhook(payload);

  // 4. Mark as processed
  await markProcessed(eventId);

  return NextResponse.json({ ok: true });
}
```

### Signature Verification

HMAC-SHA256 signature verification ensures webhook authenticity:

```typescript
// src/lib/webhooks/verify.ts
export async function verifyWebhookSignature(
  payload: string,
  signature: string
): Promise<boolean> {
  const secret = process.env.SUPABASE_WEBHOOK_SECRET!;
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload, 'utf8')
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(`sha256=${expectedSignature}`)
  );
}
```

### Environment Configuration

```bash
# Vercel environment variables
SUPABASE_WEBHOOK_SECRET=your_webhook_secret_32_chars_min
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Supabase environment (via SQL)
-- Set via supabase CLI or dashboard
-- app.vercel_webhook_url = 'https://your-app.vercel.app/api/hooks'
-- app.vercel_webhook_secret = 'your_webhook_secret'
```

### Webhook Types

| Webhook | Trigger | Purpose | Route |
|---------|---------|---------|-------|
| Trips | INSERT/UPDATE/DELETE on `trips` | Trip collaboration sync | `/api/hooks/trips` |
| Cache | Changes to cache-relevant tables | Invalidate Upstash cache | `/api/hooks/cache` |
| Files | File upload/delete events | Process attachments | `/api/hooks/files` |
| Chat | New messages/sessions | Update conversation state | `/api/hooks/chat` |

## Realtime Operations

### Supabase Realtime Architecture

Real-time functionality uses Supabase Realtime with private channels:

```sql
-- Enable RLS on realtime.messages for channel security
ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY;

-- Private channel policy
CREATE POLICY "private_channels" ON realtime.messages
  FOR ALL USING (
    realtime.topic() LIKE 'private:%' AND
    auth.uid()::text = split_part(realtime.topic(), ':', 2)
  );
```

### Channel Conventions

**Topic Naming**:

- `user:{user_id}`: User-specific notifications
- `session:{session_id}`: Chat session updates
- `trip:{trip_id}`: Trip collaboration events

**Access Control**:

- Topics prefixed with user/session/trip IDs
- RLS policies enforce ownership and collaboration permissions
- Private channels require authentication

### Frontend Realtime Integration

```typescript
// src/components/providers/realtime-auth-provider.tsx
export function RealtimeAuthProvider({ children }: { children: ReactNode }) {
  const supabase = useSupabase();

  useEffect(() => {
    // Sync access token with realtime socket
    supabase.realtime.setAuth(accessToken);

    // Join private user channel
    const userChannel = supabase.channel(`user:${userId}`, {
      config: { private: true }
    });

    userChannel.subscribe();

    return () => userChannel.unsubscribe();
  }, [accessToken, userId]);

  return <>{children}</>;
}
```

### Realtime Hooks

```typescript
// src/hooks/use-supabase-realtime.ts
export function useTripCollaboration(tripId: string) {
  const supabase = useSupabase();

  useEffect(() => {
    const channel = supabase.channel(`trip:${tripId}`, {
      config: { private: true }
    });

    channel.on('broadcast', { event: 'trip_updated' }, (payload) => {
      // Update local trip state
      queryClient.invalidateQueries(['trip', tripId]);
    });

    return () => channel.unsubscribe();
  }, [tripId]);
}
```

### Connection Management

- **Automatic reconnection**: Supabase handles connection drops
- **Presence tracking**: Online/offline status via presence channels
- **Error handling**: Graceful degradation when realtime unavailable
- **Rate limiting**: Channel subscription limits per user

## Database Monitoring

### Health Checks

Database health is monitored through multiple layers:

```sql
-- Database connection health
CREATE VIEW database_health AS
SELECT
    'active_connections' as metric,
    count(*)::text as value,
    CASE WHEN count(*) > 150 THEN 'warning' ELSE 'ok' END as status
FROM pg_stat_activity
WHERE state = 'active';
```

### Performance Metrics

```sql
-- Query performance monitoring
CREATE VIEW query_performance AS
SELECT
    query,
    calls,
    total_time / calls as avg_time,
    rows / calls as avg_rows
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

### Vector Search Performance

```sql
-- Vector index statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexname LIKE '%embedding%';
```

### Monitoring Integration

- **OpenTelemetry**: Distributed tracing for database operations
- **Custom metrics**: Query duration, connection pool utilization
- **Alerting**: Threshold-based alerts for performance degradation
- **Dashboards**: Real-time monitoring via Supabase dashboard

## Operational Procedures

### Backup and Recovery

**Automated Backups**:

- Supabase manages daily database backups
- Point-in-time recovery available
- Cross-region replication for high availability

**Manual Backup**:

```bash
# Export schema and data
supabase db dump --db-url "postgresql://..." > backup.sql

# Export specific tables
pg_dump --table=memories --table=session_memories > memories_backup.sql
```

### Schema Migrations

**Migration Process**:

1. Create migration file with timestamp prefix
2. Test migration on development database
3. Apply to staging environment
4. Deploy to production with rollback plan

**Migration Naming**:

```text
YYYYMMDD_HHMMSS_description.sql
# Example: 20251113_143000_add_trip_collaborators.sql
```

### Scaling Procedures

**Connection Pooling**:

- Supabase manages connection pools automatically
- Monitor connection utilization via `pg_stat_activity`
- Scale compute resources based on load patterns

**Vector Search Optimization**:

```sql
-- Rebuild vector indexes for better performance
REINDEX INDEX CONCURRENTLY idx_memories_embedding;

-- Adjust HNSW parameters based on data size
ALTER INDEX idx_memories_embedding
SET (m = 32, ef_construction = 400);
```

### Troubleshooting

**Common Issues**:

1. **Webhook Delivery Failures**
   - Check webhook endpoint availability
   - Verify HMAC signature configuration
   - Monitor Vercel function logs

2. **Realtime Connection Issues**
   - Validate JWT token expiration
   - Check channel permissions
   - Monitor Supabase realtime logs

3. **Performance Degradation**
   - Analyze slow queries via `pg_stat_statements`
   - Check vector index effectiveness
   - Monitor connection pool utilization

### Emergency Procedures

**Service Outage Response**:

1. Assess impact and notify stakeholders
2. Check Supabase status page
3. Implement read-only mode if database unavailable
4. Restore from backup if data corruption detected

**Data Recovery**:

1. Identify affected data and timeframe
2. Restore from point-in-time backup
3. Validate data integrity
4. Update application state

---

This operational architecture ensures reliable, scalable Supabase integration with comprehensive monitoring and recovery procedures.
