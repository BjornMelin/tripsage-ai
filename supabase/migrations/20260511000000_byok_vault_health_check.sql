-- BYOK Vault readiness check for operator health probes.
-- Returns only a boolean readiness signal; never returns decrypted secret values.

CREATE OR REPLACE FUNCTION public.check_byok_vault_health()
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_decrypted_probe TEXT;
  v_probe_name TEXT := 'tripsage_byok_health_probe_' || gen_random_uuid()::TEXT;
  v_probe_secret TEXT := 'tripsage-byok-health-probe';
BEGIN
  IF coalesce((current_setting('request.jwt.claims', true)::json->>'role'),'') <> 'service_role' THEN
    RAISE EXCEPTION 'Must be called as service role';
  END IF;

  DELETE FROM vault.secrets WHERE name = v_probe_name;
  PERFORM vault.create_secret(v_probe_secret, v_probe_name);

  SELECT s.secret
  INTO v_decrypted_probe
  FROM vault.decrypted_secrets s
  WHERE s.name = v_probe_name
  LIMIT 1;

  DELETE FROM vault.secrets WHERE name = v_probe_name;

  RETURN v_decrypted_probe = v_probe_secret;
EXCEPTION
  WHEN OTHERS THEN
    BEGIN
      DELETE FROM vault.secrets WHERE name = v_probe_name;
    EXCEPTION
      WHEN OTHERS THEN
        NULL;
    END;
    RAISE;
END;
$$;

REVOKE ALL ON FUNCTION public.check_byok_vault_health() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.check_byok_vault_health() TO service_role;
