-- Delete user memories atomically (service_role only).
-- Uses a single transaction via PL/pgSQL function execution.

CREATE OR REPLACE FUNCTION public.delete_user_memories(
  p_user_id UUID
) RETURNS TABLE (
  deleted_turns BIGINT,
  deleted_sessions BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_deleted_turns BIGINT;
  v_deleted_sessions BIGINT;
BEGIN
  IF coalesce((current_setting('request.jwt.claims', true)::json->>'role'),'') <> 'service_role' THEN
    RAISE EXCEPTION 'Must be called as service role';
  END IF;

  DELETE FROM memories.turns WHERE user_id = p_user_id;
  GET DIAGNOSTICS v_deleted_turns = ROW_COUNT;

  DELETE FROM memories.sessions WHERE user_id = p_user_id;
  GET DIAGNOSTICS v_deleted_sessions = ROW_COUNT;

  RETURN QUERY SELECT v_deleted_turns, v_deleted_sessions;
END;
$$;

