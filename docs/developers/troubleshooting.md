# Troubleshooting

Debugging techniques, CI/CD information, and development workflow guidance.

## CI/CD Pipeline

### GitHub Actions Setup

TripSage uses minimal CI/CD with GitHub Actions for quality gates:

**Jobs:**

- **Backend**: Python linting, type checking, unit tests
- **Frontend**: TypeScript checking, linting, unit tests

**Triggers:**

- Push to main/develop branches
- Pull requests to main/develop
- Changes to relevant file paths

### Quality Gates

```bash
# Python checks
ruff check . --fix    # Lint and auto-fix
ruff format .         # Format code
uv run pytest         # Run tests with coverage

# TypeScript checks
cd frontend && pnpm lint     # Lint and auto-fix
cd frontend && pnpm format   # Format code
cd frontend && pnpm test     # Run tests
```

### Path-Based Execution

CI jobs run only when relevant files change:

- Backend: `tripsage/**`, `tripsage_core/**`, `scripts/**`, `pyproject.toml`, etc.
- Frontend: `frontend/**`
- Config: `.github/workflows/**`

## Branch Workflow

### Branch Types

**Main Branches:**

- `main`: Production code, requires PR reviews
- `develop`: Integration branch for features

**Feature Branches:**

- Pattern: `feat/*` (e.g., `feat/user-authentication`)
- Created from `develop`, merged back to `develop`

**Other Branches:**

- `session/*`: Temporary work branches
- `hotfix/*`: Critical production fixes

### Git Workflow

```bash
# Feature development
git checkout develop
git checkout -b feat/new-feature
# Work on feature
git commit -m "feat: implement new feature"
git push origin feat/new-feature
# Create PR to develop

# Release process
git checkout develop
git checkout -b release/v1.2.0
# Final testing
git checkout main
git merge release/v1.2.0
```

### Commit Messages

Use conventional commits:

```bash
feat: add user authentication
fix: resolve database connection timeout
docs: update API documentation
refactor: simplify trip creation logic
```

## Debugging Techniques

### Logging

TripSage uses structured JSON logging throughout:

```python
# tripsage_core/observability/otel.py
import logging

logger = logging.getLogger(__name__)

def log_api_request(method: str, path: str, status: int, duration: float):
    logger.info(
        "API request completed",
        extra={
            "method": method,
            "path": path,
            "status_code": status,
            "duration_ms": round(duration * 1000, 2)
        }
    )
```

### Common Issues

#### Authentication Problems

**JWT Token Issues:**

```python
# Check token validity
from tripsage.api.middlewares.authentication import verify_jwt
is_valid = await verify_jwt(token)
```

**Supabase Auth Errors:**

- Check Supabase dashboard logs
- Verify client credentials
- Confirm redirect URIs match

#### Database Connection Issues

**Connection Pool Exhaustion:**

```python
# Check connection status
from tripsage_core.services.infrastructure.database_service import DatabaseService
db = DatabaseService()
status = await db.health_check()
```

**Query Performance:**

```sql
-- Enable query logging
SET log_statement = 'all';
SET log_duration = 'on';

-- Check slow queries
SELECT * FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '1 second';
```

#### API Performance Issues

**Rate Limiting:**

```python
# Check rate limit status
from tripsage.api.limiting import limiter
remaining = await limiter.get_remaining_requests(request)
```

**Caching Problems:**

```python
# Verify cache connectivity
from tripsage_core.services.infrastructure.cache_service import CacheService
cache = CacheService()
is_connected = await cache.ping()
```

### Frontend Debugging

**React Development Tools:**

- Use React DevTools for component inspection
- Check Network tab for API calls
- Monitor TanStack Query cache

**State Management:**

```typescript
// Debug Zustand state
import { useAuthStore } from '@/stores/auth-store';

// In component
const state = useAuthStore.getState();
console.log('Auth state:', state);
```

### Testing in Development

**Run Specific Tests:**

```bash
# Backend: Run specific test file
uv run pytest tests/unit/api/test_trips.py -v

# Frontend: Run specific test
cd frontend && pnpm test TripCard.test.tsx
```

**Debug Test Failures:**

```bash
# Backend: Run with debugging
uv run pytest --pdb --tb=short

# Frontend: Run with watch mode
cd frontend && pnpm test --watch
```

## Performance Optimization

### Database Optimization

**Query Analysis:**

```sql
-- Explain query execution
EXPLAIN ANALYZE SELECT * FROM trips WHERE user_id = $1;

-- Check index usage
SELECT * FROM pg_stat_user_indexes
WHERE relname = 'trips';
```

**Connection Pooling:**

```python
# Monitor pool status
from tripsage_core.config import get_settings
settings = get_settings()
pool_size = settings.db_max_connections
```

### Caching Strategies

**Cache Hit Analysis:**

```python
# Check cache effectiveness
cache_stats = await cache.get_stats()
hit_rate = cache_stats.hits / (cache_stats.hits + cache_stats.misses)
```

**Cache Invalidation:**

```python
# Clear specific cache entries
await cache.delete("user:123:trips")
await cache.delete_pattern("trip:*")
```

### Memory Management

**Monitor Memory Usage:**

```python
import psutil
import os

process = psutil.Process(os.getpid())
memory_usage = process.memory_info().rss / 1024 / 1024  # MB
```

**Profile Memory Leaks:**

```python
# Use memory_profiler
from memory_profiler import profile

@profile
def memory_intensive_function():
    # Code to profile
    pass
```

## Deployment Issues

### Container Problems

**Docker Build Issues:**

```bash
# Debug build process
docker build --no-cache --progress=plain -t tripsage .

# Check container logs
docker logs tripsage-container
```

**Health Check Failures:**

```bash
# Test health endpoint
curl -f http://localhost:8000/health

# Check container health
docker ps
docker inspect tripsage-container | grep -A 10 "Health"
```

### Environment Configuration

**Missing Environment Variables:**

```bash
# Validate configuration
python scripts/config/config_manager.py validate

# Check environment
env | grep -E "(SUPABASE|DATABASE|REDIS)"
```

**Configuration Conflicts:**

```bash
# Compare environments
python scripts/config/config_manager.py check-env production
```

## Monitoring and Alerts

### Application Metrics

**Response Times:**

- API endpoints: target <500ms for most operations
- Database queries: target <100ms
- External API calls: monitor and cache appropriately

**Error Rates:**

- Target <1% error rate for production APIs
- Monitor 4xx vs 5xx errors separately
- Set up alerts for error rate spikes

### System Resources

**CPU Usage:**

- Monitor per-service CPU utilization
- Scale horizontally when >70% sustained usage
- Profile CPU-intensive operations

**Memory Usage:**

- Monitor memory leaks in long-running processes
- Set appropriate memory limits for containers
- Use connection pooling to manage database connections

### Database Monitoring

**Connection Pool:**

```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity
WHERE datname = 'tripsage';

-- Monitor connection age
SELECT pid, usename, client_addr,
       now() - backend_start as connection_age
FROM pg_stat_activity
WHERE state = 'idle';
```

**Slow Query Analysis:**

```sql
-- Find slow queries
SELECT query, total_exec_time, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## Development Environment Issues

### Dependency Problems

**Python Dependencies:**

```bash
# Reinstall dependencies
rm -rf .venv
uv sync

# Check for conflicts
uv pip check
```

**Node Dependencies:**

```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### IDE and Tooling

**TypeScript Issues:**

```bash
# Clear TypeScript cache
cd frontend && rm -rf .next
pnpm build  # Rebuild to check types
```

**Python Type Checking:**

```bash
# Run mypy or pyright
uv run pyright .

# Check import issues
python -c "import tripsage.api.main; print('Import successful')"
```

## Getting Help

### Internal Resources

- Check team documentation in internal wiki
- Review recent changes in git history
- Check monitoring dashboards for system status

### External Resources

- Supabase documentation and community forums
- Next.js and FastAPI documentation
- PostgreSQL and Redis documentation

### Escalation Process

1. Check this troubleshooting guide
2. Review application logs and monitoring
3. Consult team documentation
4. Reach out to team members with relevant expertise
5. Escalate to infrastructure team if needed
