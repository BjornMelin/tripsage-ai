# TripSage Security Guide

Essential security implementation and best practices for TripSage operators.

## Security Architecture

TripSage implements defense-in-depth security with multiple protection layers:

- **TLS/HTTPS Encryption** - All production traffic encrypted
- **JWT Authentication** - Supabase-managed token validation
- **Rate Limiting** - Distributed counters via Redis
- **Input Validation** - Pydantic models for all API inputs
- **Row Level Security** - Database-level access control
- **Audit Logging** - Comprehensive security event logging

## Authentication & Authorization

### Authentication Methods

| Method | Use Case | Security Level |
|--------|----------|----------------|
| JWT Tokens | User sessions | High |
| API Keys | Server-to-server | High |
| BYOK Keys | Third-party services | High |

### Row Level Security (RLS)

All database tables use PostgreSQL RLS with policies for:

- **User Isolation** - Users access only their own data
- **Collaborative Access** - Shared access with permission levels
- **Admin Operations** - Restricted to service roles

```sql
-- User data isolation
CREATE POLICY "user_isolation" ON trips
FOR ALL TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

-- Collaborative access
CREATE POLICY "collaborative_access" ON trips
FOR ALL TO authenticated
USING (
  user_id = auth.uid() OR
  id IN (
    SELECT trip_id FROM trip_collaborators
    WHERE user_id = auth.uid()
  )
);
```

## Security Best Practices

### Development Security

- **Input Validation**: Use Pydantic models for all API inputs
- **Error Handling**: Never expose internal errors to users
- **Dependencies**: Keep packages updated, audit regularly
- **Secrets**: Never commit secrets, use environment variables

### Operational Security

- **HTTPS**: Required in production
- **CORS**: Properly configured origins
- **Monitoring**: Log authentication failures and suspicious activity
- **Backups**: Regular encrypted database backups

### BYOK (Bring Your Own Key) System

Secure third-party API key management:

- **Encryption**: AES-256 with user-specific salts
- **Storage**: Encrypted in database with RLS protection
- **Access**: Users can only access their own keys
- **Audit**: All key operations logged

## Security Testing

### Automated Testing

```bash
# Dependency vulnerability scanning
uv run safety check

# Static security analysis
uv run bandit -r tripsage/

# Secret detection
uv run detect-secrets scan
```

### Manual Testing

```bash
# Test authentication
curl -H "Authorization: Bearer invalid_token" \
     http://localhost:8000/api/trips
# Expected: 401 Unauthorized

# Test rate limiting
for i in {1..150}; do
  curl http://localhost:8000/api/trips
done
# Expected: 429 Too Many Requests
```

## Security Checklist

### Pre-Deployment

- [ ] Secrets in environment variables only
- [ ] HTTPS enabled in production
- [ ] RLS policies tested and verified
- [ ] Rate limiting configured
- [ ] Security headers set
- [ ] Dependencies scanned for vulnerabilities

### Production Monitoring

- [ ] Authentication failure alerts
- [ ] Unusual traffic pattern detection
- [ ] Security log analysis
- [ ] Regular vulnerability scanning

### Maintenance

- [ ] Security patch updates applied
- [ ] Dependencies kept current
- [ ] Regular security audits
- [ ] Incident response procedures tested
