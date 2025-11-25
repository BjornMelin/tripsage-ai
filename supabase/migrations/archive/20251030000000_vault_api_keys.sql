-- Supabase Vault-backed BYOK schema
-- Date: 2025-10-30

-- 1) Enable Vault extension
CREATE EXTENSION IF NOT EXISTS vault WITH SCHEMA vault;

-- 2) api_keys metadata table (no secrets here)
CREATE TABLE IF NOT EXISTS public.api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  service TEXT NOT NULL,
  vault_secret_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_used TIMESTAMPTZ,
  CONSTRAINT api_keys_user_service_uniq UNIQUE (user_id, service)
);

-- 3) RLS: owner-only
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'api_keys' AND policyname = 'api_keys_owner_crud'
  ) THEN
    CREATE POLICY "api_keys_owner_crud" ON public.api_keys
      FOR ALL
      USING (auth.uid() = user_id)
      WITH CHECK (auth.uid() = user_id);
  END IF;
END $$;

-- 4) Helper functions (SECURITY DEFINER) restricted to service_role
-- Notes:
--  - We check current_setting('role', true) to limit invocation to service_role.
--  - Secrets are created/deleted in vault.* and only the vault secret name is stored in public.api_keys

CREATE OR REPLACE FUNCTION public.insert_user_api_key(
  p_user_id UUID,
  p_service TEXT,
  p_api_key TEXT
) RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_secret_id UUID;
  v_service TEXT := lower(trim(p_service));
  v_secret_name TEXT := v_service || '_api_key_' || p_user_id::TEXT;
BEGIN
  IF coalesce((current_setting('request.jwt.claims', true)::json->>'role'),'') <> 'service_role' THEN
    RAISE EXCEPTION 'Must be called as service role';
  END IF;

  -- Create or replace secret in Vault
  -- If a secret with the same name exists, delete it first to ensure replacement
  DELETE FROM vault.secrets WHERE name = v_secret_name;
  v_secret_id := vault.create_secret(p_api_key, v_secret_name);

  INSERT INTO public.api_keys(user_id, service, vault_secret_name, created_at, last_used)
  VALUES(p_user_id, v_service, v_secret_name, now(), NULL)
  ON CONFLICT (user_id, service)
  DO UPDATE SET vault_secret_name = EXCLUDED.vault_secret_name,
                created_at = now(),
                last_used = NULL;

  RETURN v_secret_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.get_user_api_key(
  p_user_id UUID,
  p_service TEXT
) RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_secret TEXT;
  v_service TEXT := lower(trim(p_service));
  v_secret_name TEXT := v_service || '_api_key_' || p_user_id::TEXT;
BEGIN
  IF coalesce((current_setting('request.jwt.claims', true)::json->>'role'),'') <> 'service_role' THEN
    RAISE EXCEPTION 'Must be called as service role';
  END IF;

  SELECT s.secret INTO v_secret
  FROM vault.decrypted_secrets s
  WHERE s.name = v_secret_name
  LIMIT 1;

  RETURN v_secret;
END;
$$;

CREATE OR REPLACE FUNCTION public.delete_user_api_key(
  p_user_id UUID,
  p_service TEXT
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_service TEXT := lower(trim(p_service));
  v_secret_name TEXT := v_service || '_api_key_' || p_user_id::TEXT;
BEGIN
  IF coalesce((current_setting('request.jwt.claims', true)::json->>'role'),'') <> 'service_role' THEN
    RAISE EXCEPTION 'Must be called as service role';
  END IF;

  DELETE FROM vault.secrets WHERE name = v_secret_name;
  DELETE FROM public.api_keys WHERE user_id = p_user_id AND service = v_service;
END;
$$;

-- 5) Convenience: bump last_used when explicitly called (optional)
CREATE OR REPLACE FUNCTION public.touch_user_api_key(
  p_user_id UUID,
  p_service TEXT
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_service TEXT := lower(trim(p_service));
BEGIN
  IF coalesce((current_setting('request.jwt.claims', true)::json->>'role'),'') <> 'service_role' THEN
    RAISE EXCEPTION 'Must be called as service role';
  END IF;
  UPDATE public.api_keys SET last_used = now() WHERE user_id = p_user_id AND service = v_service;
END;
$$;
