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
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=... # canonical (sb_publishable_...)
# Legacy fallback: set NEXT_PUBLIC_SUPABASE_ANON_KEY only if publishable key is unavailable
SUPABASE_SERVICE_ROLE_KEY=...

# Team Gateway fallback (optional)
AI_GATEWAY_API_KEY=...
AI_GATEWAY_URL=...                                  # optional baseURL override
AI_GATEWAY_ALLOWED_HOSTS=my-gateway.vercel.sh       # required for non-default Gateway hosts

# Optional provider fallbacks (server-only)
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
XAI_API_KEY=...
OPENROUTER_API_KEY=...
```

## Migrations to Verify

- `supabase/migrations/20260120000000_base_schema.sql` (squashed)
  - Tables: `api_gateway_configs` (owner RLS), `user_settings` (owner RLS, `allow_gateway_fallback` default false).
  - RPCs (SECURITY DEFINER, service_role only): `upsert_user_gateway_config`, `get_user_gateway_base_url`, `delete_user_gateway_config`, `get_user_allow_gateway_fallback`.

## Verification (service role curl)

```bash
# Insert user Gateway key
curl -X POST https://<project>.supabase.co/rest/v1/rpc/insert_user_api_key \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id":"00000000-0000-0000-0000-000000000001","p_service":"gateway","p_api_key":"sk-gateway"}'

# Store optional user Gateway base URL
curl -X POST https://<project>.supabase.co/rest/v1/rpc/upsert_user_gateway_config \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id":"00000000-0000-0000-0000-000000000001","p_base_url":"https://my-gateway.vercel.sh/v3/ai"}'

# Read back base URL
curl -X POST https://<project>.supabase.co/rest/v1/rpc/get_user_gateway_base_url \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id":"00000000-0000-0000-0000-000000000001"}'

# Consent toggle
curl -X POST https://<project>.supabase.co/rest/v1/rpc/get_user_allow_gateway_fallback \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id":"00000000-0000-0000-0000-000000000001"}'
```

**Expected:**

- Gateway config RPCs succeed with service role, fail with anon key.
- `allow_gateway_fallback` respects user setting default false.

## Provider Resolution Order (code contract)

1. User Gateway key (Vercel AI Gateway)  
2. User provider BYOK keys (OpenAI/Anthropic/xAI/OpenRouter)  
3. Team fallback `AI_GATEWAY_API_KEY` if user consent `allowGatewayFallback=true`  
4. Server provider keys only when Gateway is not configured

All resolution happens server-side (`@ai/models/registry`); keys are never exposed to the client.

## App Endpoints to Exercise

- `POST /api/keys` — insert BYOK or Gateway key (`service:"gateway"` optional `baseUrl`).
- `POST /api/user-settings` — set `allowGatewayFallback`.
- `POST /api/keys/validate` — authenticated user route to validate a provider key without persisting it.
- `GET /api/health/byok` — operator-only readiness route. Send `x-internal-key: $BYOK_HEALTHCHECK_KEY`; the backing RPC creates, decrypts, and deletes a non-user probe secret, and the response contains Vault/RPC status only.

## Security Notes

- Secrets live in Vault; access only via SECURITY DEFINER RPCs with service role JWT.
- BYOK routes are `"server-only"` and dynamic (no static rendering).
- Do not log API keys; telemetry spans redact secrets.

## Troubleshooting

- **401/403 on /api/keys/validate**: user authentication missing or rejected by route guards before provider validation.
- **401/403 on /api/health/byok**: missing or invalid `BYOK_HEALTHCHECK_KEY`; rotate the health token if the value may have leaked.
- **503 `VAULT_UNAVAILABLE` on /api/health/byok**: check `SUPABASE_SERVICE_ROLE_KEY`, the `check_byok_vault_health()` migration, Vault extension status, and service-role RPC execution.
- **No fallback despite team key**: ensure `allowGatewayFallback=true` for user and `AI_GATEWAY_API_KEY` set.
- **High latency resolving provider**: check Vault availability; reduce repeated lookups or cache consent in request scope.
- **RPC denied**: verify migrations applied and functions marked SECURITY DEFINER; call with service role token.

## Change Management Checklist

- [ ] Migrations applied and RLS enabled on `api_gateway_configs` / `user_settings`.
- [ ] Env vars set (`SUPABASE_*`, optional `AI_GATEWAY_*`, provider keys if needed).
- [ ] Service-role curl smoke tests pass (insert/get gateway config, consent read).
- [ ] Team fallback path tested by removing user keys and setting consent ON.
- [ ] Logs/telemetry reviewed for secret redaction.
