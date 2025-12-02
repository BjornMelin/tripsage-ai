# TripSage Security Guide

Essential security implementation and best practices for TripSage operators.

## Security Architecture

TripSage implements defense-in-depth security with multiple protection layers:

- **TLS/HTTPS Encryption** - All production traffic encrypted
- **JWT Authentication** - Supabase-managed token validation
- **Rate Limiting** - Distributed counters via Upstash Redis
- **Input Validation** - Zod v4 schemas for all API inputs
- **Row Level Security** - Database-level access control
- **Audit Logging** - Comprehensive security event logging via OpenTelemetry
- **Session Control** - User-scoped session listing and termination via `/api/security/sessions` with Supabase service-role enforcement and per-route rate limits.

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

- **Input Validation**: Use Zod v4 schemas for all API inputs (see `@schemas/*`)
- **Error Handling**: Never expose internal errors to users
- **Dependencies**: Keep packages updated, audit regularly via `pnpm audit`
- **Secrets**: Never commit secrets, use environment variables

### Operational Security

- **HTTPS**: Required in production
- **CORS**: Properly configured origins
- **Monitoring**: Log authentication failures and suspicious activity
- **Backups**: Regular encrypted database backups
- **MFA Ops**:
  - **Environment variables & precedence**:
    - Configure `MFA_BACKUP_CODE_PEPPER` (>=16 chars) in every environment:
      - Local development: `.env.local`
      - CI: CI/CD secret store
      - Preview/production: deployment platform secret manager
    - Configure `SUPABASE_JWT_SECRET` (>=16 chars) as the JWT signing key.
    - Backup-code hashing always prefers `MFA_BACKUP_CODE_PEPPER`; `SUPABASE_JWT_SECRET` is used only as a bootstrap fallback when the pepper is absent. Rotating the JWT secret while using it as a fallback pepper invalidates existing backup codes.
    - Example generation (run once per environment): `openssl rand -hex 32`.
  - **Relationship and intended use**:
    - `MFA_BACKUP_CODE_PEPPER`: deterministic pepper for backup-code hashing/salting only.
    - `SUPABASE_JWT_SECRET`: JWT signing key for Supabase auth tokens.
    - Do **not** treat these as interchangeable secrets. Using `SUPABASE_JWT_SECRET` as a backup-code pepper is a compatibility fallback only and should be phased out by setting a dedicated `MFA_BACKUP_CODE_PEPPER`.
  - **Support-driven recovery**:
    - Definition: admin-initiated account recovery flows (e.g., regenerating backup codes for a locked-out user, clearing a stuck enrollment, or disabling a compromised factor).
    - Requirements:
      - Operator identity verified at AAL2 before performing recovery operations.
      - All recovery operations linked to a ticket/incident ID in the support system.
      - Every recovery operation writes an audit event and is reviewable by security/ops.
  - **Audit trail & monitoring**:
    - Backup-code lifecycle events are logged to the `mfa_backup_code_audit` table (see `supabase/migrations/20251122000000_base_schema.sql`) with the following fields:
      - `id` (UUID, PK), `user_id` (UUID), `event` (`"regenerated"` | `"consumed"`), `count` (integer), `ip` (text), `user_agent` (text), `created_at` (timestamptz).
    - Integrate failures into existing observability:
      - On insert failure, `@/lib/security/mfa.ts` emits `mfa backup code audit insert failed` errors and increments counters; surface these via OpenTelemetry traces and logs into PagerDuty/Slack.
      - Configure database retention or scheduled cleanup for `mfa_backup_code_audit` so PII fields (`ip`, `user_agent`) are retained only as long as needed for forensics.

| Variable / Table              | Purpose                              | Min Length | Precedence / Notes                                                                                   |
| ----------------------------- | ------------------------------------ | ---------- | ---------------------------------------------------------------------------------------------------- |
| `MFA_BACKUP_CODE_PEPPER`      | Backup-code hashing pepper           | ≥ 16 chars | Preferred source; used for all backup-code hashing when set.                                        |
| `SUPABASE_JWT_SECRET`         | JWT signing key (Supabase)          | ≥ 16 chars | Used as fallback pepper **only** when `MFA_BACKUP_CODE_PEPPER` is unset; rotate carefully.          |
| `mfa_backup_code_audit` table | Backup-code regeneration/consumption | N/A        | Schema defined in `supabase/migrations/20251122000000_base_schema.sql`; used for long-lived audit.  |

### BYOK (Bring Your Own Key) System

Secure third-party API key management:

- **Encryption**: Vault extension with service-role-only access
- **Storage**: Encrypted in Supabase Vault with RLS protection
- **Access**: Users can only access their own keys via server-side checks; there are no `dynamic = "force-dynamic"` API route files/exports under `frontend/src/app/api`, so enforcement relies on backend logic and Supabase RLS rather than Next.js route caching directives.
- **Audit**: Telemetry infrastructure exists, but BYOK RPCs (`insertUserApiKey`, `deleteUserApiKey`, `getUserApiKey` in `frontend/src/lib/supabase/rpc.ts`) are not currently wrapped in OpenTelemetry spans. To enable tracing, wrap these calls with `withTelemetrySpan` in a shared helper before invoking the RPCs.

## Security Testing

### Automated Testing

```bash
# Dependency vulnerability scanning
pnpm audit

# TypeScript type checking (catches schema issues)
pnpm -C frontend type-check

# Run security-focused tests
pnpm -C frontend test:run -t security

# Secret detection (install gitleaks first)
gitleaks detect --source . --verbose
```

### Manual Testing

```bash
# Test authentication
curl -H "Authorization: Bearer invalid_token" \
     http://localhost:3000/api/trips
# Expected: 401 Unauthorized

# Test rate limiting
for i in {1..150}; do
  curl http://localhost:3000/api/trips
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
