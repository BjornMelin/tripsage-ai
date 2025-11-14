# Title: Add per-user AI Gateway BYOK support and consent setting

**Date**: 2025-11-13

**Summary**: Add per-user AI Gateway BYOK support and consent setting

- Add `service='gateway'` support to BYOK storage (Vault-backed secret).
- Add `public.api_gateway_configs` to store optional per-user Gateway base URL (non-secret metadata) with owner-only RLS.
- Add `public.user_settings.allow_gateway_fallback` with owner-only RLS and default true.
- Add SECURITY DEFINER RPCs (service_role only): `upsert_user_gateway_config`, `get_user_gateway_base_url`, `delete_user_gateway_config`, `get_user_allow_gateway_fallback`.

## Why

- Some users want to route exclusively through their own Vercel AI Gateway account. We support a per-user Gateway key and optional base URL. Consent allows users to forbid team Gateway fallback if they prefer strict BYOK.

## How to verify

1) Apply migrations.
2) POST /api/keys with `{ service: 'gateway', apiKey, baseUrl? }` returns 204.
3) GET /api/keys shows `gateway` entry with non-secret metadata.
4) DELETE /api/keys/gateway removes secret and config.
5) Registry resolves per-user Gateway when present; otherwise resolves per-user provider keys; otherwise (if allow_gateway_fallback=true) resolves team Gateway; else throws.
