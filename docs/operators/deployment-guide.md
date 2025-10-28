# Production Deployment Guide

## Pre-Deployment Checklist

### Environment Preparation

- [ ] Database migration scripts tested
- [ ] Environment variables configured
- [ ] Upstash Redis credentials set (UPSTASH_REDIS_REST_URL/TOKEN)
- [ ] SSL certificates installed
- [ ] Domain DNS configured

### Build Validation

- [ ] TypeScript compilation clean: `npm run type-check`
- [ ] Frontend build successful: `npm run build`
- [ ] Backend tests passing: `pytest`
- [ ] Security validation complete: `python scripts/security/security_validation.py`

## Deployment Sequence

### 1. Database Migration

```bash
# Run database migrations
python scripts/database/run_migrations.py

# Verify pgvector optimization
python -c "from tripsage_core.services.infrastructure.database_service import DatabaseService; print('✅ Database service ready')"
```

### 2. Cache System Setup

```bash
# Configure Upstash Redis (managed) — no local container required
# Verify connection
python scripts/verification/verify_upstash.py
```

### 3. Frontend Deployment

```bash
cd frontend
npm ci --production
npm run build
npm start
```

### 4. Backend Deployment

```bash
uv install --production
uv run python -m tripsage.api.main
```

## Performance Monitoring

### Key Metrics to Monitor

- Vector search latency: Target <20ms
- Database connection pool: Target <80% utilization
- Realtime channels: Monitor authorization errors and reconnect rates
- Memory usage: Target <512MB per service
- Cache hit rate: Target >90%

### Monitoring Endpoints

- Health check: `GET /api/health`
- Metrics: `GET /api/metrics`
- Database status: `GET /api/health/database`
- Realtime status: use Supabase Dashboard Realtime metrics; backend exposes only `GET /api/health`

## Troubleshooting

### Common Issues

#### Database Connection Issues

```bash
# Check connection
python scripts/verification/verify_connection.py

# Reset connection pool
docker restart tripsage-database
```

#### Realtime Subscription Failures

```bash
# Common causes
# 1) Missing/expired access token in supabase.realtime.setAuth()
# 2) Topic not authorized by RLS policies (see supabase/migrations/20251027_01_realtime_policies.sql)
# 3) Realtime Authorization disabled in Supabase project settings
```

#### Performance Degradation

```bash
# Run performance benchmark
python scripts/benchmarks/benchmark.py --database-only

# Check resource usage
htop
iotop
```

## Rollback Procedure

### Emergency Rollback

1. Switch traffic to previous version
2. Revert database migrations if needed
3. Clear cache to prevent stale data
4. Monitor error rates

### Database Rollback

```bash
# Backup current state
pg_dump tripsage > backup_$(date +%Y%m%d_%H%M%S).sql

# Revert migrations (if needed)
python scripts/database/rollback_migrations.py --to-version <previous_version>
```

## Security Considerations

### Production Security Settings

- CORS origins restricted to production domains
- Supabase Realtime Authorization enabled (private channels only)
- Rate limiting configured for production load
- API keys rotated and secured
- Database connection strings encrypted

### Security Validation

```bash
# Run security audit
python scripts/security/security_validation.py

# Check for vulnerabilities
bandit -r . -f json -o security_report.json
```

## Performance Optimization Tips

### Database Optimization

- Monitor query performance with `EXPLAIN ANALYZE`
- Keep pgvector indexes optimized
- Use connection pooling efficiently
- Monitor disk I/O and memory usage

### Frontend Optimization

- Enable production build optimizations
- Use CDN for static assets
- Monitor Core Web Vitals
- Implement proper caching headers

### WebSocket Optimization

- Monitor connection count
- Use Redis pub/sub for scaling
- Implement proper error recovery
- Monitor heartbeat performance

---

> *Deployment guide for TripSage AI platform*
