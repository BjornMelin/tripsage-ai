# BYOK + Vercel AI Gateway Operator Runbook

Operational checklist for user BYOK, Vault, and team Gateway fallback.

## Scope

- User-scoped AI keys for OpenAI/Anthropic/xAI/OpenRouter.
- User Vercel AI Gateway keys and base URLs.
- Team fallback via `AI_GATEWAY_API_KEY` when consented.
- Alignment with Supabase Vault + SECURITY DEFINER RPCs.

## Prerequisites

- Supabase project with Vault enabled.
- Service role key available for ops verification.
- Migrations applied (see below).
- Frontend deployed with `"server-only"` BYOK routes kept dynamic.

## Environment Variables

```bash
# Supabase (required)
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

# Team Gateway fallback (optional)
AI_GATEWAY_API_KEY=...
AI_GATEWAY_URL=https://ai-gateway.vercel.sh/v1   # optional override

# Optional provider fallbacks (server-only)
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
XAI_API_KEY=...
OPENROUTER_API_KEY=...
```

## Migrations to Verify

- `supabase/migrations/20251113000000_gateway_user_byok.sql`
  - Tables: `api_gateway_configs` (owner RLS), `user_settings` (owner RLS, `allow_gateway_fallback` default true).
  - RPCs (SECURITY DEFINER, service_role only): `upsert_user_gateway_config`, `get_user_gateway_base_url`, `delete_user_gateway_config`, `get_user_allow_gateway_fallback`.

## Verification (service role curl)

```bash
# Insert user Gateway key + base URL
curl -X POST https://<project>.supabase.co/rest/v1/rpc/upsert_user_gateway_config \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id":"test-user","p_base_url":"https://my-gateway.vercel.sh/v1","p_api_key":"sk-gateway"}'

# Read back base URL
curl -X POST https://<project>.supabase.co/rest/v1/rpc/get_user_gateway_base_url \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id":"test-user"}'

# Consent toggle
curl -X POST https://<project>.supabase.co/rest/v1/rpc/get_user_allow_gateway_fallback \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id":"test-user"}'
```

**Expected:**

- Gateway config RPCs succeed with service role, fail with anon key.
- `allow_gateway_fallback` respects user setting default true.

## Provider Resolution Order (code contract)

1. User Gateway key (Vercel AI Gateway)  
2. User provider BYOK keys (OpenAI/Anthropic/xAI/OpenRouter)  
3. Team fallback `AI_GATEWAY_API_KEY` if user consent `allowGatewayFallback=true`  

All resolution happens server-side (`@/lib/providers/registry`); keys are never exposed to the client.

## App Endpoints to Exercise

- `POST /api/keys` — insert BYOK or Gateway key (`service:"gateway"` optional `baseUrl`).
- `POST /api/user-settings` — set `allowGatewayFallback`.
- `POST /api/keys/validate` — validate key; expect 401/403 on invalid or consent denial.

## Security Notes

- Secrets live in Vault; access only via SECURITY DEFINER RPCs with service role JWT.
- BYOK routes are `"server-only"` and dynamic (no static rendering).
- Do not log API keys; telemetry spans redact secrets.

## Troubleshooting

- **401/403 on /api/keys/validate**: key invalid, consent off, or missing service role in RPC call.
- **No fallback despite team key**: ensure `allowGatewayFallback=true` for user and `AI_GATEWAY_API_KEY` set.
- **High latency resolving provider**: check Vault availability; reduce repeated lookups or cache consent in request scope.
- **RPC denied**: verify migrations applied and functions marked SECURITY DEFINER; call with service role token.

## Change Management Checklist

- [ ] Migrations applied and RLS enabled on `api_gateway_configs` / `user_settings`.
- [ ] Env vars set (`SUPABASE_*`, optional `AI_GATEWAY_*`, provider keys if needed).
- [ ] Service-role curl smoke tests pass (insert/get gateway config, consent read).
- [ ] Team fallback path tested by removing user keys and setting consent ON.
- [ ] Logs/telemetry reviewed for secret redaction.
