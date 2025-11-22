-- Vault role hardening: dedicate a definer role with least privilege.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'api_vault_definer'
  ) THEN
    CREATE ROLE api_vault_definer NOLOGIN;
  END IF;
END $$;

-- Ensure the role can access vault schema primitives only as needed
GRANT USAGE ON SCHEMA vault TO api_vault_definer;
-- Revoke broad access from PUBLIC
REVOKE ALL ON ALL TABLES IN SCHEMA vault FROM PUBLIC;
REVOKE ALL ON SCHEMA vault FROM PUBLIC;

-- Minimal table privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON vault.secrets TO api_vault_definer;
GRANT SELECT ON vault.decrypted_secrets TO api_vault_definer;

-- Allow executing Vault functions (create/update) without superuser
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA vault TO api_vault_definer;

-- Make SECURITY DEFINER functions run with the restricted role
ALTER FUNCTION public.insert_user_api_key(UUID, TEXT, TEXT) OWNER TO api_vault_definer;
ALTER FUNCTION public.get_user_api_key(UUID, TEXT) OWNER TO api_vault_definer;
ALTER FUNCTION public.delete_user_api_key(UUID, TEXT) OWNER TO api_vault_definer;
ALTER FUNCTION public.touch_user_api_key(UUID, TEXT) OWNER TO api_vault_definer;

