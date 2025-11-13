---
date: 2025-11-13
status: current
---

# BYOK + Vercel AI Gateway Operator Runbook

## Overview

**BYOK + Vercel AI Gateway Operator** enables **per-user Bring Your Own Key (BYOK)**
across **OpenAI**, **Anthropic**, **xAI**, and **OpenRouter** with **team Gateway fallback**.

- **Consent-controlled**: Users explicitly **allow/disallow** team Gateway fallback
- **Security-first**: All secrets live in **Supabase Vault**; routes are **server-only**
  and **fully dynamic**

## Prerequisites

### Supabase Setup

- **Supabase project** with **Vault enabled**

### Environment Variables

Deployed environment with the following **environment variables**:

**Public Variables:**

- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`

**Server-only Variables:**

- `SUPABASE_SERVICE_ROLE_KEY` (**server-only**)
- `AI_GATEWAY_API_KEY` (**server-only**; optional team fallback)
- `AI_GATEWAY_URL=<https://ai-gateway.vercel.sh/v1>` (optional override)
- `OPENAI_API_KEY` / `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` / `XAI_API_KEY`
  (optional server fallbacks)

## Migrations

### 1. Apply Database Migration

Apply migration: `supabase/migrations/20251113000000_gateway_user_byok.sql`

### 2. Verify Tables and Policies

Verify the following **tables and policies** are created:

- `public.api_gateway_configs` (**owner RLS**)
- `public.user_settings` (**owner RLS**, `allow_gateway_fallback` default `TRUE`)

### 3. Verify SECURITY DEFINER RPCs

Verify the following **SECURITY DEFINER RPCs** are restricted to `service_role`:

- `upsert_user_gateway_config`, `get_user_gateway_base_url`, `delete_user_gateway_config`
- `get_user_allow_gateway_fallback`

## Verification Checklist

### 1. User Gateway BYOK

- Insert user Gateway API key via `POST /api/keys` with `service:"gateway"`
  and optional `baseUrl` (https)
- Confirm `resolveProvider` returns `path=user-gateway`, `provider=gateway`

### 2. Provider BYOK

- Insert provider key (`openai`/`openrouter`/`anthropic`/`xai`) via `POST /api/keys`
- Confirm `resolveProvider` returns `path=user-provider` and correct provider tag

### 3. Team Gateway Fallback

- Ensure `AI_GATEWAY_API_KEY` is set; remove user/provider BYOK keys; set consent **ON**
  via `POST /api/user-settings`
- Confirm `resolveProvider` returns `path=team-gateway`, `provider=gateway`

### 4. Consent Enforcement

- With consent **OFF** (`POST /api/user-settings { allowGatewayFallback:false }`), no BYOK keys
  → expect error

## Operational Notes

### Security Best Practices

- **Do not log secrets**. Routes `import "server-only"` and
  `export const dynamic = "force-dynamic"`

### Telemetry

- Telemetry spans (`name: providers.resolve`) include `baseUrlHost` and
  `baseUrlSource` (`user|team`)

### Advanced Configuration

- `ProviderOptions` for Gateway can be passed in route handlers to influence routing
  (see README examples)

## Troubleshooting

### Common Issues

**401/403 on `/api/keys/validate`:**

- Key invalid or rate limit exceeded

**No fallback despite `AI_GATEWAY_API_KEY`:**

- User consent may be **OFF**; toggle via `POST /api/user-settings`

**High latency:**

- Reduce Vault fetch fanout or cache preference checks per request
