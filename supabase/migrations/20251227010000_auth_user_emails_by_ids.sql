-- Lookup auth user emails by ids (service-role only).
-- This avoids N+1 Admin getUserById calls when listing collaborators.
CREATE OR REPLACE FUNCTION public.auth_user_emails_by_ids(p_user_ids UUID[])
RETURNS TABLE (user_id UUID, email TEXT)
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = auth, public, pg_temp
AS $$
  SELECT u.id, u.email
  FROM auth.users u
  WHERE u.id = ANY (p_user_ids);
$$;

REVOKE ALL ON FUNCTION public.auth_user_emails_by_ids(UUID[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.auth_user_emails_by_ids(UUID[]) TO service_role;
