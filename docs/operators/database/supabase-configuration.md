# Supabase BYOK Security Verification & Operations Guide

## Overview

This document outlines the verification and operational procedures for the sophisticated Supabase BYOK (Bring Your Own Key) implementation. This system provides multi-provider AI API key management with enterprise-grade security through Vault storage, RPC hardening, and comprehensive access controls.

## Architecture Overview

The BYOK system consists of:

- **Factory Pattern**: `@supabase/ssr` integration with OpenTelemetry tracing
- **Multi-Provider Support**: OpenAI, Anthropic, xAI, OpenRouter, Vercel AI Gateway
- **Vault Storage**: Encrypted API key storage with service-role access only
- **RPC Security**: All operations via SECURITY DEFINER functions
- **RLS Isolation**: Owner-only data access policies
- **SSR Compatibility**: Next.js App Router with proper cookie handling

## Prerequisites

- Supabase project with Vault extension enabled
- Service role key access for administrative operations
- Environment variables configured (see [BYOK Gateway Operator Runbook](../runbooks/byok-gateway-operator.md))

## Automated Verification

### Using the Verification Script

The system includes verification procedures to test all security components:

> Run comprehensive BYOK security verification via curl commands
> See manual verification tasks below for specific operations

This verification covers:

- ✅ Vault extension accessibility
- ✅ Role hardening and access controls
- ✅ RPC function security
- ✅ BYOK storage/retrieval operations
- ✅ Gateway configuration
- ✅ User settings management
- ✅ RLS data isolation
- ✅ Multi-provider support

### Manual Verification Tasks

#### 1. Vault Extension & Role Verification

**Check Vault Extension:**

```bash
# Verify Vault is accessible via RPC
curl -X POST https://your-project.supabase.co/rest/v1/rpc/get_user_api_key \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test-user-id", "p_service": "openai"}'
```

Expected: `null` (no key exists) or permission error (Vault working)

#### 2. SECURITY DEFINER Function Verification

**Test Function Access Control:**

```bash
# This should fail (permission denied)
curl -X POST https://your-project.supabase.co/rest/v1/rpc/insert_user_api_key \
  -H "Authorization: Bearer anon-key" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test", "p_service": "openai", "p_api_key": "test"}'

# This should work (service role)
curl -X POST https://your-project.supabase.co/rest/v1/rpc/insert_user_api_key \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test", "p_service": "openai", "p_api_key": "test"}'
```

#### 3. BYOK Operations Testing

**Complete BYOK Lifecycle Test:**

```bash
# 1. Insert API key
curl -X POST https://your-project.supabase.co/rest/v1/rpc/insert_user_api_key \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test-user", "p_service": "openai", "p_api_key": "sk-test-key"}'

# 2. Retrieve API key
curl -X POST https://your-project.supabase.co/rest/v1/rpc/get_user_api_key \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test-user", "p_service": "openai"}'

# 3. Update last_used timestamp
curl -X POST https://your-project.supabase.co/rest/v1/rpc/touch_user_api_key \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test-user", "p_service": "openai"}'

# 4. Delete API key
curl -X POST https://your-project.supabase.co/rest/v1/rpc/delete_user_api_key \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test-user", "p_service": "openai"}'
```

#### 4. Gateway Configuration Testing

**Test Gateway BYOK:**

```bash
# Set user Gateway config
curl -X POST https://your-project.supabase.co/rest/v1/rpc/upsert_user_gateway_config \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test-user", "p_base_url": "https://my-gateway.vercel.sh/v1"}'

# Get user Gateway config
curl -X POST https://your-project.supabase.co/rest/v1/rpc/get_user_gateway_base_url \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test-user"}'

# Check Gateway fallback setting
curl -X POST https://your-project.supabase.co/rest/v1/rpc/get_user_allow_gateway_fallback \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test-user"}'
```

#### 5. RLS Data Isolation Testing

**Test Data Isolation:**

```sql
-- As service role, insert test data
SELECT insert_user_api_key('user-a', 'openai', 'key-a');
SELECT insert_user_api_key('user-b', 'openai', 'key-b');

-- As user-a (should only see their data)
-- This would be tested through the application RLS policies
```

## Operational Procedures

### Pre-Deployment Checklist

> **Note**: This is a reusable deployment checklist template. Copy and complete for each deployment.

- [ ] **Automated Verification**: All manual verification tasks pass
- [ ] **Migration Verification**: All BYOK migrations applied (`20251030000000_vault_api_keys.sql`, `20251030002000_vault_role_hardening.sql`, `20251113000000_gateway_user_byok.sql`)
- [ ] **Environment Variables**: All required secrets configured (service role key, API keys, Gateway URL)
- [ ] **Vault Extension**: Enabled and accessible
- [ ] **RPC Functions**: All 8 SECURITY DEFINER functions operational
- [ ] **RLS Policies**: Owner-only access policies active
- [ ] **Multi-Provider**: All 5 providers (OpenAI, Anthropic, xAI, OpenRouter, Gateway) functional

### Monitoring & Observability

#### Telemetry Integration

The BYOK system integrates with OpenTelemetry for comprehensive observability:

- **Factory Initialization**: `supabase.init` spans with database connection tracking
- **Provider Resolution**: `providers.resolve` spans with user ID redaction and path tracking
- **Auth Operations**: `supabase.auth.getUser` spans for session management
- **Middleware**: Session refresh spans in Edge runtime

#### Key Metrics to Monitor

```sql
# BYOK resolution success rate
sum(rate(providers_resolve_total{status="success"}[5m])) /
sum(rate(providers_resolve_total[5m]))

# Vault operation latency
histogram_quantile(0.95, rate(vault_operation_duration_bucket[5m]))

# RLS policy violations
rate(rls_policy_violation_total[5m])
```

#### Alert Conditions

- BYOK resolution failure rate > 5%
- Vault operation latency > 500ms p95
- RLS policy violations > 0
- Missing API keys for active users

### Troubleshooting Guide

#### Common Issues

##### "Vault extension not accessible"

```bash
# Check Vault extension status
supabase db sql "SELECT name, installed_version FROM pg_available_extensions WHERE name = 'vault';"

# Re-enable if needed
supabase db sql "CREATE EXTENSION IF NOT EXISTS vault;"
```

##### "Must be called as service role"

- Verify service role key is correct and has required permissions
- Check JWT claims include `role: "service_role"`
- Ensure RPC calls use proper authorization headers

##### "RLS policy violation"

```sql
-- Check RLS policies are active
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('api_keys', 'api_gateway_configs', 'user_settings');
```

##### "Provider resolution failed"

- Check API key validity for the provider
- Verify provider is supported (openai, anthropic, xai, openrouter, gateway)
- Check Gateway fallback settings if no BYOK keys

#### Emergency Procedures

**Disable BYOK for All Users:**

```sql
-- Remove all API keys (emergency only)
DELETE FROM vault.secrets WHERE name LIKE '%_api_key_%';
DELETE FROM public.api_keys;
```

**Reset User Gateway Settings:**

```sql
-- Reset to defaults
UPDATE public.user_settings SET allow_gateway_fallback = true;
DELETE FROM public.api_gateway_configs;
```

## Security Considerations

### Defense in Depth

1. **Network Level**: Supabase project access controls
2. **Application Level**: Service role key authentication
3. **Database Level**: RLS policies and SECURITY DEFINER functions
4. **Encryption Level**: Vault-stored secrets with Supabase encryption
5. **Operational Level**: Audit logging and monitoring

### Compliance Requirements

- **Data Encryption**: All API keys encrypted at rest via Vault
- **Access Logging**: All operations logged with user context
- **Principle of Least Privilege**: Service role only for administrative operations
- **Data Isolation**: RLS ensures users only access their own keys
- **Regular Audits**: Automated verification scripts for continuous compliance

### Incident Response

**API Key Compromise:**

1. Immediately revoke compromised key via BYOK interface
2. Audit access logs for unauthorized usage
3. Rotate affected API keys at provider
4. Update BYOK with new keys

**Vault Security Breach:**

1. Assess breach scope and impact
2. Rotate all affected API keys
3. Review and update access controls
4. Enhance monitoring and alerting

## Integration Testing

### End-to-End BYOK Flow

```typescript
// Test from application perspective
import { resolveProvider } from "@ai/models/registry";

// Should use BYOK key if available
const provider = await resolveProvider(userId, "gpt-4o-mini");
expect(provider.provider).toBe("openai");
expect(provider.modelId).toBe("gpt-4o-mini");

// Should fallback to team Gateway
// (remove BYOK keys and ensure Gateway configured)
const fallbackProvider = await resolveProvider(userId, "gpt-4o-mini");
expect(fallbackProvider.path).toBe("team-gateway");
```

### SSR Compatibility Testing

```typescript
// Test Next.js App Router integration
import { createServerSupabase } from "@/lib/supabase/server";
import { getCurrentUser } from "@/lib/supabase/factory";

// Should work in Server Components
const supabase = await createServerSupabase();
const user = await getCurrentUser(supabase);
expect(user).toBeDefined();
```

## Related Documentation

- [BYOK Gateway Operator Runbook](../runbooks/byok-gateway-operator.md)
- [Provider Registry Implementation](../../src/lib/providers/registry.ts)
- [Supabase Factory Pattern](../../src/lib/supabase/factory.ts)
- [Vault RPC Operations](../../src/lib/supabase/rpc.ts)
- [SSR Middleware](../../middleware.ts)
