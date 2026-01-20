-- Adds a minimal, safe-by-default audit trail for inbound webhooks/jobs.
-- Stores hashes and allowlisted headers only (no raw bodies or secrets).

-- NOTE: Supabase CLI can restore `supabase_migrations.schema_migrations` from a cached local backup.
-- If the tracking row for this migration already exists, the CLI will fail at the end when recording
-- the migration version. Make the migration idempotent by deleting any pre-existing row (when present).
DO $do$
BEGIN
  IF to_regclass('supabase_migrations.schema_migrations') IS NOT NULL THEN
    DELETE FROM supabase_migrations.schema_migrations WHERE version = '20260119020000';
  END IF;
END;
$do$;

CREATE TABLE IF NOT EXISTS public.inbound_webhook_receipts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL CHECK (
    source IN ('stripe', 'qstash', 'supabase_outbound', 'other')
  ),
  handler TEXT NOT NULL,
  request_id TEXT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  signature_valid BOOLEAN NOT NULL DEFAULT false,
  idempotency_key TEXT NULL,
  body_sha256 TEXT NOT NULL,
  headers_subset JSONB NOT NULL DEFAULT '{}'::jsonb,
  result_status INTEGER NOT NULL,
  error_code TEXT NULL,
  error_message TEXT NULL
);

CREATE INDEX IF NOT EXISTS inbound_webhook_receipts_source_received_at_idx
  ON public.inbound_webhook_receipts (source, received_at DESC);

CREATE INDEX IF NOT EXISTS inbound_webhook_receipts_request_id_idx
  ON public.inbound_webhook_receipts (request_id);

ALTER TABLE public.inbound_webhook_receipts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS inbound_webhook_receipts_service_all ON public.inbound_webhook_receipts;
CREATE POLICY inbound_webhook_receipts_service_all
  ON public.inbound_webhook_receipts
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

DROP POLICY IF EXISTS inbound_webhook_receipts_admin_read ON public.inbound_webhook_receipts;
CREATE POLICY inbound_webhook_receipts_admin_read
  ON public.inbound_webhook_receipts
  FOR SELECT
  TO authenticated
  USING (public.is_admin());
