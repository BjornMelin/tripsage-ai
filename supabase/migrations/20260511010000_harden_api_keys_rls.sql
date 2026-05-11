-- Harden BYOK metadata RLS so user sessions can read their own key metadata
-- but all metadata mutations stay behind service-role RPC/API paths.

ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS api_keys_owner ON public.api_keys;
DROP POLICY IF EXISTS api_keys_owner_crud ON public.api_keys;
DROP POLICY IF EXISTS api_keys_owner_select ON public.api_keys;
DROP POLICY IF EXISTS api_keys_service ON public.api_keys;

REVOKE ALL ON TABLE public.api_keys FROM authenticated;
GRANT SELECT ON TABLE public.api_keys TO authenticated;
GRANT ALL ON TABLE public.api_keys TO service_role;

CREATE POLICY api_keys_owner_select
  ON public.api_keys
  FOR SELECT
  TO authenticated
  USING ((select auth.uid()) = user_id);

CREATE POLICY api_keys_service
  ON public.api_keys
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
