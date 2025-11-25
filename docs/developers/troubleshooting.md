# Troubleshooting

Debugging techniques, CI/CD information, and development workflow guidance.

## CI/CD Pipeline

### GitHub Actions Setup

TripSage uses minimal CI/CD with GitHub Actions for quality gates:

**Jobs:**

- **Frontend**: TypeScript checking, linting, unit tests

**Triggers:**

- Push to main/develop branches
- Pull requests to main/develop
- Changes to relevant file paths

### Quality Gates

```bash
# TypeScript checks
cd frontend && pnpm biome:check    # Lint and auto-fix
cd frontend && pnpm biome:fix      # Format code
cd frontend && pnpm type-check     # Type checking
cd frontend && pnpm test           # Run tests
```

### Path-Based Execution

CI jobs run only when relevant files change:

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

### Common Issues

#### Authentication Problems

**Supabase Auth Errors:**

- Check Supabase dashboard logs
- Verify client credentials
- Confirm redirect URIs match

#### Database Connection Issues

**Query Performance:**

```sql
-- Enable query logging
SET log_statement = 'all';
SET log_duration = 'on';

-- Check slow queries
SELECT * FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '1 second';
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
# Frontend: Run specific test
cd frontend && pnpm test TripCard.test.tsx
```

**Debug Test Failures:**

```bash
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

### Caching Strategies

**Cache Invalidation:**

Cache invalidation is handled automatically by Next.js and Supabase. For manual cache clearing during development:

- Restart the development server to clear Next.js cache
- Use Supabase dashboard to clear database caches if needed

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
curl -f http://localhost:3000/api/health

# Check container health
docker ps
docker inspect tripsage-container | grep -A 10 "Health"
```

### Environment Configuration

**Missing Environment Variables:**

```bash
# Check environment
env | grep -E "(SUPABASE|DATABASE|REDIS|AI_GATEWAY)"
```

**Configuration Conflicts:**

Compare environment variables across deployment environments using your deployment platform's configuration management.

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

## Getting Help

### Internal Resources

- Check team documentation in internal wiki
- Review recent changes in git history
- Check monitoring dashboards for system status

### External Resources

- Supabase documentation and community forums
- Next.js documentation
- PostgreSQL and Redis documentation
- Vercel AI SDK documentation

### Escalation Process

1. Check this troubleshooting guide
2. Review application logs and monitoring
3. Consult team documentation
4. Reach out to team members with relevant expertise
5. Escalate to infrastructure team if needed
