-- Per-user Gateway BYOK support and user settings for fallback consent

-- 1) Gateway config table: base URL per user (non-secret metadata)
CREATE TABLE IF NOT EXISTS public.api_gateway_configs (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  base_url TEXT
);

ALTER TABLE public.api_gateway_configs ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'api_gateway_configs' AND policyname = 'gateway_cfg_owner_crud'
  ) THEN
    CREATE POLICY "gateway_cfg_owner_crud" ON public.api_gateway_configs
      FOR ALL
      USING (auth.uid() = user_id)
      WITH CHECK (auth.uid() = user_id);
  END IF;
END $$;

-- 2) User settings (consent)
CREATE TABLE IF NOT EXISTS public.user_settings (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  allow_gateway_fallback BOOLEAN NOT NULL DEFAULT TRUE
);

ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'user_settings' AND policyname = 'user_settings_owner_crud'
  ) THEN
    CREATE POLICY "user_settings_owner_crud" ON public.user_settings
      FOR ALL
      USING (auth.uid() = user_id)
      WITH CHECK (auth.uid() = user_id);
  END IF;
END $$;

-- 3) SECURITY DEFINER RPCs, restricted to service_role

CREATE OR REPLACE FUNCTION public.upsert_user_gateway_config(
  p_user_id UUID,
  p_base_url TEXT
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF coalesce((current_setting('request.jwt.claims', true)::json->>'role'),'') <> 'service_role' THEN
    RAISE EXCEPTION 'Must be called as service role';
  END IF;
  INSERT INTO public.api_gateway_configs(user_id, base_url)
  VALUES(p_user_id, p_base_url)
  ON CONFLICT (user_id)
  DO UPDATE SET base_url = EXCLUDED.base_url;
END;
$$;

CREATE OR REPLACE FUNCTION public.get_user_gateway_base_url(
  p_user_id UUID
) RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE v_base TEXT; BEGIN
  IF coalesce((current_setting('request.jwt.claims', true)::json->>'role'),'') <> 'service_role' THEN
    RAISE EXCEPTION 'Must be called as service role';
  END IF;
  SELECT base_url INTO v_base FROM public.api_gateway_configs WHERE user_id = p_user_id;
  RETURN v_base;
END; $$;

CREATE OR REPLACE FUNCTION public.delete_user_gateway_config(
  p_user_id UUID
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF coalesce((current_setting('request.jwt.claims', true)::json->>'role'),'') <> 'service_role' THEN
    RAISE EXCEPTION 'Must be called as service role';
  END IF;
  DELETE FROM public.api_gateway_configs WHERE user_id = p_user_id;
END; $$;

CREATE OR REPLACE FUNCTION public.get_user_allow_gateway_fallback(
  p_user_id UUID
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE v_flag BOOLEAN; BEGIN
  IF coalesce((current_setting('request.jwt.claims', true)::json->>'role'),'') <> 'service_role' THEN
    RAISE EXCEPTION 'Must be called as service role';
  END IF;
  SELECT allow_gateway_fallback INTO v_flag FROM public.user_settings WHERE user_id = p_user_id;
  IF v_flag IS NULL THEN
    RETURN TRUE; -- default allow
  END IF;
  RETURN v_flag;
END; $$;
