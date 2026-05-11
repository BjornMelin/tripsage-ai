-- Harden AI SDK v6 chat/tool and Gateway fallback contracts for existing DBs.

ALTER TABLE public.chat_tool_calls
  ADD COLUMN IF NOT EXISTS provider_executed boolean;

UPDATE public.chat_tool_calls
SET provider_executed = false
WHERE provider_executed IS NULL;

ALTER TABLE public.chat_tool_calls
  ALTER COLUMN provider_executed SET DEFAULT false,
  ALTER COLUMN provider_executed SET NOT NULL;

ALTER TABLE public.user_settings
  ALTER COLUMN allow_gateway_fallback SET DEFAULT false;

UPDATE public.user_settings
SET allow_gateway_fallback = false
WHERE allow_gateway_fallback IS NULL;

CREATE OR REPLACE FUNCTION public.get_user_allow_gateway_fallback(
  p_user_id uuid
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_flag boolean;
BEGIN
  IF coalesce((current_setting('request.jwt.claims', true)::json->>'role'), '') <> 'service_role' THEN
    RAISE EXCEPTION 'Must be called as service role';
  END IF;

  SELECT allow_gateway_fallback
  INTO v_flag
  FROM public.user_settings
  WHERE user_id = p_user_id;

  RETURN coalesce(v_flag, false);
END;
$$;

REVOKE ALL ON FUNCTION public.get_user_allow_gateway_fallback(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_user_allow_gateway_fallback(uuid) FROM anon;
REVOKE ALL ON FUNCTION public.get_user_allow_gateway_fallback(uuid) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.get_user_allow_gateway_fallback(uuid) TO service_role;

DROP POLICY IF EXISTS "chat_messages_insert" ON public.chat_messages;
DROP POLICY IF EXISTS chat_messages_insert ON public.chat_messages;
CREATE POLICY chat_messages_insert
  ON public.chat_messages
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = (select auth.uid())
    AND role = 'user'
    AND session_id IN (
      SELECT id FROM public.chat_sessions
      WHERE user_id = (select auth.uid())
      OR trip_id IN (
        SELECT id FROM public.trips WHERE user_id = (select auth.uid())
        UNION
        SELECT trip_id FROM public.trip_collaborators WHERE user_id = (select auth.uid())
      )
    )
  );

DROP POLICY IF EXISTS "chat_messages_service_insert" ON public.chat_messages;
DROP POLICY IF EXISTS chat_messages_service_insert ON public.chat_messages;
CREATE POLICY chat_messages_service_insert
  ON public.chat_messages
  FOR INSERT
  TO service_role
  WITH CHECK (true);

DROP POLICY IF EXISTS "chat_tool_calls_insert" ON public.chat_tool_calls;
DROP POLICY IF EXISTS chat_tool_calls_insert ON public.chat_tool_calls;
CREATE POLICY chat_tool_calls_insert
  ON public.chat_tool_calls
  FOR INSERT
  TO service_role
  WITH CHECK (true);

DROP POLICY IF EXISTS "api_gateway_configs_owner" ON public.api_gateway_configs;
DROP POLICY IF EXISTS api_gateway_configs_owner ON public.api_gateway_configs;
CREATE POLICY api_gateway_configs_owner
  ON public.api_gateway_configs
  FOR SELECT
  TO authenticated
  USING ((select auth.uid()) = user_id);
