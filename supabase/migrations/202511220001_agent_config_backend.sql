-- Agent configuration backend tables and RLS
-- Created: 2025-11-22

-- helper: admin check from JWT claims
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
  SELECT coalesce(
    nullif(current_setting('request.jwt.claims', true)::json ->> 'is_admin', ''),
    current_setting('request.jwt.claims', true)::json -> 'user_metadata' ->> 'is_admin'
  ) = 'true';
$$;

-- agent_config_versions: append-only history
CREATE TABLE IF NOT EXISTS public.agent_config_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_type text NOT NULL,
  scope text NOT NULL DEFAULT 'global',
  config jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid REFERENCES auth.users(id),
  summary text
);

CREATE INDEX IF NOT EXISTS agent_config_versions_agent_scope_created_idx
  ON public.agent_config_versions(agent_type, scope, created_at DESC);

-- agent_config: active record per (agent_type, scope)
CREATE TABLE IF NOT EXISTS public.agent_config (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_type text NOT NULL,
  scope text NOT NULL DEFAULT 'global',
  config jsonb NOT NULL,
  version_id uuid NOT NULL REFERENCES public.agent_config_versions(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT agent_config_unique UNIQUE (agent_type, scope)
);

CREATE INDEX IF NOT EXISTS agent_config_agent_scope_idx
  ON public.agent_config(agent_type, scope);

-- atomic upsert + version insertion
CREATE OR REPLACE FUNCTION public.agent_config_upsert(
  p_agent_type text,
  p_scope text,
  p_config jsonb,
  p_created_by uuid,
  p_summary text DEFAULT NULL
)
RETURNS TABLE(version_id uuid, config jsonb)
LANGUAGE plpgsql
AS $$
DECLARE
  v_version_id uuid;
BEGIN
  INSERT INTO public.agent_config_versions(agent_type, scope, config, created_by, summary)
  VALUES (p_agent_type, p_scope, p_config, p_created_by, p_summary)
  RETURNING id, config INTO v_version_id, config;

  INSERT INTO public.agent_config(agent_type, scope, config, version_id)
  VALUES (p_agent_type, p_scope, p_config, v_version_id)
  ON CONFLICT (agent_type, scope)
  DO UPDATE SET
    config = EXCLUDED.config,
    version_id = v_version_id,
    updated_at = now();

  RETURN QUERY SELECT v_version_id, config;
END;
$$;

-- updated_at trigger
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_agent_config_updated_at'
  ) THEN
    CREATE TRIGGER trg_agent_config_updated_at
      BEFORE UPDATE ON public.agent_config
      FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
END$$;

-- RLS policies
ALTER TABLE public.agent_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_config_versions ENABLE ROW LEVEL SECURITY;

-- service_role full access
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='agent_config' AND policyname='agent_config_service_all'
  ) THEN
    CREATE POLICY agent_config_service_all ON public.agent_config
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='agent_config_versions' AND policyname='agent_config_versions_service_all'
  ) THEN
    CREATE POLICY agent_config_versions_service_all ON public.agent_config_versions
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

-- admin-only access for authenticated users
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='agent_config' AND policyname='agent_config_admin_all'
  ) THEN
    CREATE POLICY agent_config_admin_all ON public.agent_config
      FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='agent_config_versions' AND policyname='agent_config_versions_admin_all'
  ) THEN
    CREATE POLICY agent_config_versions_admin_all ON public.agent_config_versions
      FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;
END$$;
