-- TripSage consolidated init schema
-- Generated: 2026-01-20
-- This file replaces all prior migrations (pre-deployment consolidation). Do not split unless required by production change management.

-- NOTE: Supabase CLI can restore `supabase_migrations.schema_migrations` from a cached local backup.
-- If the tracking row for this migration already exists, the CLI will fail at the end when recording
-- the migration version. Make the migration idempotent by deleting any pre-existing row (when present).
DO $do$
BEGIN
  IF to_regclass('supabase_migrations.schema_migrations') IS NOT NULL THEN
    DELETE FROM supabase_migrations.schema_migrations WHERE version = '20260120000000';
  END IF;
END;
$do$;

-- ===========================
-- EXTENSIONS
-- ===========================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "pg_cron";
CREATE EXTENSION IF NOT EXISTS "pg_net";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
DO $$
DECLARE
  env TEXT := lower(coalesce(
    current_setting('app.environment', true),
    current_setting('app.settings.environment', true),
    'development'
  ));
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vault') THEN
    EXECUTE 'CREATE EXTENSION IF NOT EXISTS vault WITH SCHEMA vault';
  ELSE
    IF env IN ('production', 'prod') THEN
      RAISE EXCEPTION 'vault extension is required in production (env=%); deploy supabase_vault or vault extension before running migrations.', env;
    ELSE
      RAISE NOTICE 'vault extension not available in %; BYOK RPCs will be stubbed', env;
    END IF;
  END IF;
END;
$$;

-- Stub vault structures for local/CI environments without the extension
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_extension WHERE extname IN ('vault', 'supabase_vault')
  ) THEN
    CREATE SCHEMA IF NOT EXISTS vault;
    CREATE TABLE IF NOT EXISTS vault.secrets (
      name TEXT PRIMARY KEY,
      secret TEXT
    );
    CREATE OR REPLACE VIEW vault.decrypted_secrets AS
    SELECT name, secret FROM vault.secrets;
    CREATE OR REPLACE FUNCTION vault.create_secret(p_secret TEXT, p_name TEXT)
    RETURNS UUID
    LANGUAGE plpgsql
    AS $f$
    BEGIN
      INSERT INTO vault.secrets(name, secret)
      VALUES (p_name, p_secret)
      ON CONFLICT (name) DO UPDATE SET secret = EXCLUDED.secret;
      RETURN md5(random()::TEXT || clock_timestamp()::TEXT)::UUID;
    END;
    $f$;
  END IF;
END;
$$;

-- ===========================
-- CORE TABLES
-- ===========================

-- auth_backup_codes (MFA backup codes)
CREATE TABLE IF NOT EXISTS public.auth_backup_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  code_hash TEXT NOT NULL CHECK (length(code_hash) <= 256),
  label TEXT DEFAULT 'primary' CHECK (label IN ('primary','secondary','recovery') AND length(label) <= 32),
  issued_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
  consumed_at TIMESTAMPTZ,
  CONSTRAINT auth_backup_codes_consumed_after_issue CHECK (consumed_at IS NULL OR consumed_at >= issued_at)
);

CREATE UNIQUE INDEX IF NOT EXISTS auth_backup_codes_user_code_hash_idx
  ON public.auth_backup_codes (user_id, code_hash);

-- Track active primary backup codes per user for fast lookup (non-unique)
CREATE INDEX IF NOT EXISTS auth_backup_codes_primary_active_idx
  ON public.auth_backup_codes (user_id)
  WHERE label = 'primary' AND consumed_at IS NULL;

-- Support cleanup/audit queries for consumed codes
CREATE INDEX IF NOT EXISTS auth_backup_codes_consumed_at_idx
  ON public.auth_backup_codes (user_id, consumed_at)
  WHERE consumed_at IS NOT NULL;

ALTER TABLE public.auth_backup_codes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role can manage backup codes" ON public.auth_backup_codes;
CREATE POLICY "Service role can manage backup codes"
  ON public.auth_backup_codes
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Atomic replacement of MFA backup codes (service-role only)
CREATE OR REPLACE FUNCTION public.replace_backup_codes(
  p_user_id uuid,
  p_code_hashes text[]
) returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  inserted integer := 0;
begin
  delete from public.auth_backup_codes
  where user_id = p_user_id;

  insert into public.auth_backup_codes (user_id, code_hash)
  select p_user_id, code_hash
  from unnest(p_code_hashes) as t(code_hash);

  get diagnostics inserted = row_count;
  return inserted;
end;
$$;

grant execute on function public.replace_backup_codes(uuid, text[]) to service_role;

comment on function public.replace_backup_codes(uuid, text[]) is 'Atomically replaces all backup codes for a user with the provided hashed list.';

-- Audit log for backup code lifecycle
CREATE TABLE IF NOT EXISTS public.mfa_backup_code_audit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  event TEXT NOT NULL CHECK (event IN ('regenerated','consumed')),
  count INTEGER NOT NULL DEFAULT 0,
  ip TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS mfa_backup_code_audit_user_created_idx
  ON public.mfa_backup_code_audit (user_id, created_at DESC);

ALTER TABLE public.mfa_backup_code_audit ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own backup code audit" ON public.mfa_backup_code_audit;
CREATE POLICY "Users can view own backup code audit"
  ON public.mfa_backup_code_audit
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role manages backup code audit" ON public.mfa_backup_code_audit;
CREATE POLICY "Service role manages backup code audit"
  ON public.mfa_backup_code_audit
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

COMMENT ON TABLE public.mfa_backup_code_audit IS 'Audit trail for MFA backup code regeneration and consumption events.';

-- mfa_enrollments pending/consumed lifecycle
CREATE TABLE IF NOT EXISTS public.mfa_enrollments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  factor_id VARCHAR(255) NOT NULL,
  challenge_id VARCHAR(255) NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','consumed','expired')),
  issued_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ,
  CONSTRAINT mfa_enrollments_expiry CHECK (expires_at > issued_at),
  CONSTRAINT mfa_enrollments_consumed_after_issue CHECK (consumed_at IS NULL OR consumed_at >= issued_at)
);

CREATE INDEX IF NOT EXISTS mfa_enrollments_user_status_idx
  ON public.mfa_enrollments (user_id, status);
CREATE INDEX IF NOT EXISTS mfa_enrollments_challenge_idx
  ON public.mfa_enrollments (challenge_id);

ALTER TABLE public.mfa_enrollments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own mfa_enrollments" ON public.mfa_enrollments;
CREATE POLICY "Users can view own mfa_enrollments"
  ON public.mfa_enrollments
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role manages mfa_enrollments" ON public.mfa_enrollments;
CREATE POLICY "Service role manages mfa_enrollments"
  ON public.mfa_enrollments
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Cleanup job for expired/consumed enrollments (requires pg_cron)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
    IF NOT EXISTS (
      SELECT 1 FROM cron.job WHERE jobname = 'mfa_enrollments_cleanup_daily'
    ) THEN
      PERFORM cron.schedule(
        'mfa_enrollments_cleanup_daily',
        '0 3 * * *',
        $cron$DELETE FROM public.mfa_enrollments
            WHERE status IN ('expired','consumed')
              AND expires_at < now() - interval '1 day';$cron$
      );
    END IF;
  END IF;
END;
$$;

-- profiles (user metadata + admin flag)
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT,
  avatar_url TEXT,
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS profiles_admin_idx ON public.profiles (is_admin) WHERE is_admin = true;

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Profiles owner select" ON public.profiles;
CREATE POLICY "Profiles owner select" ON public.profiles
  FOR SELECT TO authenticated USING (auth.uid() = id);
DROP POLICY IF EXISTS "Profiles owner update" ON public.profiles;
CREATE POLICY "Profiles owner update" ON public.profiles
  FOR UPDATE TO authenticated USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
DROP POLICY IF EXISTS "Profiles owner insert" ON public.profiles;
CREATE POLICY "Profiles owner insert" ON public.profiles
  FOR INSERT TO authenticated WITH CHECK (auth.uid() = id);
DROP POLICY IF EXISTS "Profiles service all" ON public.profiles;
CREATE POLICY "Profiles service all" ON public.profiles
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- trips
CREATE TABLE IF NOT EXISTS public.trips (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    destination TEXT NOT NULL,
    description TEXT,
    budget NUMERIC NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'USD',
    travelers INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'planning',
    trip_type TEXT NOT NULL DEFAULT 'leisure',
    flexibility JSONB DEFAULT '{}',
    tags TEXT[],
    search_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT trips_date_check CHECK (end_date >= start_date),
    CONSTRAINT trips_travelers_check CHECK (travelers > 0),
    CONSTRAINT trips_budget_check CHECK (budget >= 0),
    CONSTRAINT trips_status_check CHECK (status IN ('planning','booked','completed','cancelled')),
    CONSTRAINT trips_type_check CHECK (trip_type IN ('leisure','business','family','solo','other'))
);

-- trip_collaborators
CREATE TABLE IF NOT EXISTS public.trip_collaborators (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('viewer', 'editor', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (trip_id, user_id)
);

-- chat_sessions
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id BIGINT REFERENCES public.trips(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- chat_messages
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- chat_tool_calls
CREATE TABLE IF NOT EXISTS public.chat_tool_calls (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES public.chat_messages(id) ON DELETE CASCADE,
    tool_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_message TEXT
);

-- itinerary_items
CREATE TABLE IF NOT EXISTS public.itinerary_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    item_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    price NUMERIC,
    currency TEXT,
    metadata JSONB DEFAULT '{}',
    external_id TEXT,
    booking_status TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- flights (minimal stub from base schema)
CREATE TABLE IF NOT EXISTS public.flights (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date DATE NOT NULL,
    return_date DATE,
    flight_class TEXT NOT NULL DEFAULT 'economy',
    price NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    airline TEXT,
    flight_number TEXT,
    booking_status TEXT NOT NULL DEFAULT 'available',
    external_id TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT flights_price_check CHECK (price >= 0),
    CONSTRAINT flights_class_check CHECK (flight_class IN ('economy','premium_economy','business','first')),
    CONSTRAINT flights_status_check CHECK (booking_status IN ('available','reserved','booked','cancelled'))
);

-- accommodations (generic per-trip lodging records for UI cache)
CREATE TABLE IF NOT EXISTS public.accommodations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    address TEXT,
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    room_type TEXT,
    price_per_night NUMERIC NOT NULL,
    total_price NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    rating NUMERIC,
    amenities TEXT[],
    booking_status TEXT NOT NULL DEFAULT 'available',
    external_id TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT accommodations_price_check CHECK (price_per_night >= 0 AND total_price >= 0),
    CONSTRAINT accommodations_dates_check CHECK (check_out_date > check_in_date),
    CONSTRAINT accommodations_rating_check CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)),
    CONSTRAINT accommodations_status_check CHECK (booking_status IN ('available','reserved','booked','cancelled'))
);

-- bookings (Amadeus/Stripe)
CREATE TABLE IF NOT EXISTS public.bookings (
  id TEXT PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  property_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('CONFIRMED','PENDING','CANCELLED','REFUNDED')),
  booking_token TEXT,
  stripe_payment_intent_id TEXT,
  provider_booking_id TEXT NOT NULL,
  checkin DATE NOT NULL,
  checkout DATE NOT NULL,
  guest_email TEXT NOT NULL,
  guest_name TEXT NOT NULL,
  guest_phone TEXT,
  guests INT NOT NULL CHECK (guests > 0 AND guests <= 16),
  special_requests TEXT,
  trip_id BIGINT REFERENCES public.trips(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- accommodation_embeddings (pgvector 1536-d)
CREATE TABLE IF NOT EXISTS public.accommodation_embeddings (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL CHECK (source IN ('hotel','vrbo')),
  name TEXT,
  description TEXT,
  amenities TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  embedding vector(1536)
);

DO $$
DECLARE
  v_hnsw_m integer := COALESCE(NULLIF(current_setting('PGVECTOR_HNSW_M', true), '')::integer, 32);
  v_hnsw_ef_construction integer := COALESCE(
    NULLIF(current_setting('PGVECTOR_HNSW_EF_CONSTRUCTION', true), '')::integer,
    180
  );
BEGIN
  EXECUTE format(
    'CREATE INDEX IF NOT EXISTS accommodation_embeddings_embedding_idx ON public.accommodation_embeddings USING hnsw (embedding vector_l2_ops) WITH (m = %s, ef_construction = %s);',
    v_hnsw_m,
    v_hnsw_ef_construction
  );
END;
$$;
CREATE INDEX IF NOT EXISTS accommodation_embeddings_source_idx ON public.accommodation_embeddings(source);
CREATE INDEX IF NOT EXISTS accommodation_embeddings_created_at_idx ON public.accommodation_embeddings(created_at DESC);

-- gateway BYOK (from 20251113000000)
CREATE TABLE IF NOT EXISTS public.gateway_user_keys (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  encrypted_key TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, provider)
);

ALTER TABLE public.gateway_user_keys ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "gateway_user_keys_owner" ON public.gateway_user_keys;
CREATE POLICY gateway_user_keys_owner ON public.gateway_user_keys FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "gateway_user_keys_service" ON public.gateway_user_keys;
CREATE POLICY gateway_user_keys_service ON public.gateway_user_keys FOR ALL TO service_role USING (true) WITH CHECK (true);

-- API gateway configuration (BYOK base URL) and user settings
CREATE TABLE IF NOT EXISTS public.api_gateway_configs (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  base_url TEXT
);

CREATE TABLE IF NOT EXISTS public.user_settings (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  allow_gateway_fallback BOOLEAN NOT NULL DEFAULT TRUE
);

-- API keys metadata (vault-backed secret names)
CREATE TABLE IF NOT EXISTS public.api_keys (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  service TEXT NOT NULL,
  vault_secret_name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_used TIMESTAMPTZ,
  CONSTRAINT api_keys_user_service_uniq UNIQUE (user_id, service)
);

-- storage buckets (attachments, avatars, trip-images)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types, avif_autodetection)
VALUES ('attachments','attachments',false,52428800, ARRAY['application/pdf','application/msword','application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','text/plain','text/csv','image/jpeg','image/png','image/gif','image/webp','image/svg+xml'], false)
ON CONFLICT (id) DO UPDATE SET public=EXCLUDED.public, file_size_limit=EXCLUDED.file_size_limit, allowed_mime_types=EXCLUDED.allowed_mime_types, avif_autodetection=EXCLUDED.avif_autodetection;

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types, avif_autodetection)
VALUES ('avatars','avatars',true,5242880, ARRAY['image/jpeg','image/png','image/gif','image/webp','image/avif'], true)
ON CONFLICT (id) DO UPDATE SET public=EXCLUDED.public, file_size_limit=EXCLUDED.file_size_limit, allowed_mime_types=EXCLUDED.allowed_mime_types, avif_autodetection=EXCLUDED.avif_autodetection;

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types, avif_autodetection)
VALUES ('trip-images','trip-images',false,20971520, ARRAY['image/jpeg','image/png','image/gif','image/webp','image/avif','image/heic','image/heif'], true)
ON CONFLICT (id) DO UPDATE SET public=EXCLUDED.public, file_size_limit=EXCLUDED.file_size_limit, allowed_mime_types=EXCLUDED.allowed_mime_types, avif_autodetection=EXCLUDED.avif_autodetection;

-- file processing queue
CREATE TABLE IF NOT EXISTS public.file_processing_queue (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    file_attachment_id UUID NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('virus_scan','thumbnail_generation','ocr','compression')),
    priority INTEGER NOT NULL DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','failed','cancelled')),
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    scheduled_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- file versions
CREATE TABLE IF NOT EXISTS public.file_versions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    file_attachment_id UUID NOT NULL,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL CHECK (file_size > 0),
    checksum TEXT NOT NULL,
    created_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_current BOOLEAN NOT NULL DEFAULT false,
    change_description TEXT,
    CONSTRAINT file_versions_unique UNIQUE (file_attachment_id, version_number)
);

-- memories schema for conversational memory
CREATE SCHEMA IF NOT EXISTS memories;

CREATE TABLE IF NOT EXISTS memories.sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  last_synced_at TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memories.turns (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES memories.sessions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
  content JSONB NOT NULL,
  attachments JSONB NOT NULL DEFAULT '[]'::jsonb,
  tool_calls JSONB NOT NULL DEFAULT '[]'::jsonb,
  tool_results JSONB NOT NULL DEFAULT '[]'::jsonb,
  pii_scrubbed BOOLEAN NOT NULL DEFAULT FALSE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memories.turn_embeddings (
  turn_id UUID PRIMARY KEY REFERENCES memories.turns(id) ON DELETE CASCADE,
  embedding vector(1536) NOT NULL,
  model TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- file attachments (storage metadata)
CREATE TABLE IF NOT EXISTS public.file_attachments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  trip_id BIGINT REFERENCES public.trips(id) ON DELETE CASCADE,
  chat_id uuid REFERENCES public.chat_sessions(id) ON DELETE SET NULL,
  chat_message_id BIGINT REFERENCES public.chat_messages(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  file_size BIGINT NOT NULL CHECK (file_size > 0),
  mime_type TEXT NOT NULL,
  file_path TEXT NOT NULL,
  bucket_name TEXT NOT NULL DEFAULT 'attachments',
  upload_status TEXT NOT NULL DEFAULT 'uploading' CHECK (upload_status IN ('uploading','completed','failed')),
  virus_scan_status TEXT NOT NULL DEFAULT 'pending' CHECK (virus_scan_status IN ('pending','clean','infected','failed')),
  virus_scan_result JSONB NOT NULL DEFAULT '{}'::jsonb,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- rag_documents (hybrid RAG storage; composite key supports chunking)
CREATE TABLE IF NOT EXISTS public.rag_documents (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  chunk_index INT NOT NULL DEFAULT 0,
  content TEXT NOT NULL,
  embedding vector(1536),
  metadata JSONB DEFAULT '{}'::jsonb,
  namespace TEXT NOT NULL DEFAULT 'default' CHECK (
    namespace IN ('default', 'accommodations', 'destinations', 'activities', 'travel_tips', 'user_content')
  ),
  source_id TEXT,
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  trip_id bigint REFERENCES public.trips(id) ON DELETE CASCADE,
  chat_id uuid REFERENCES public.chat_sessions(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  fts tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
  CONSTRAINT rag_documents_pkey PRIMARY KEY (id, chunk_index),
  CONSTRAINT rag_documents_trip_requires_user_check CHECK (trip_id IS NULL OR user_id IS NOT NULL)
);

DO $$
DECLARE
  v_hnsw_m integer := COALESCE(NULLIF(current_setting('PGVECTOR_HNSW_M', true), '')::integer, 32);
  v_hnsw_ef_construction integer := COALESCE(
    NULLIF(current_setting('PGVECTOR_HNSW_EF_CONSTRUCTION', true), '')::integer,
    180
  );
BEGIN
  EXECUTE format(
    'CREATE INDEX IF NOT EXISTS rag_documents_embedding_idx ON public.rag_documents USING hnsw (embedding vector_cosine_ops) WITH (m = %s, ef_construction = %s);',
    v_hnsw_m,
    v_hnsw_ef_construction
  );
END;
$$;

CREATE INDEX IF NOT EXISTS rag_documents_namespace_idx ON public.rag_documents(namespace);
CREATE INDEX IF NOT EXISTS rag_documents_source_id_idx ON public.rag_documents(source_id) WHERE source_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS rag_documents_created_at_idx ON public.rag_documents(created_at DESC);
CREATE INDEX IF NOT EXISTS rag_documents_fts_idx ON public.rag_documents USING gin(fts);
CREATE INDEX IF NOT EXISTS rag_documents_user_id_idx ON public.rag_documents(user_id);
CREATE INDEX IF NOT EXISTS rag_documents_trip_id_idx ON public.rag_documents(trip_id);
CREATE INDEX IF NOT EXISTS rag_documents_chat_id_idx ON public.rag_documents(chat_id);

COMMENT ON TABLE public.rag_documents IS 'Generic RAG document store with pgvector embeddings for semantic search (SPEC-0104).';
COMMENT ON COLUMN public.rag_documents.embedding IS 'Vector embedding (1536 dimensions) from OpenAI text-embedding-3-small.';
COMMENT ON COLUMN public.rag_documents.namespace IS 'Logical partition for organizing documents by domain (not an auth boundary).';
COMMENT ON COLUMN public.rag_documents.source_id IS 'Reference to original document for chunk lineage tracking.';
COMMENT ON COLUMN public.rag_documents.chunk_index IS 'Index of chunk within source document (0-based).';
COMMENT ON COLUMN public.rag_documents.fts IS 'Full-text search tsvector for keyword matching.';

-- saved_places (trip-scoped POIs with collaboration-aware RLS)
CREATE TABLE IF NOT EXISTS public.saved_places (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL DEFAULT 'googleplaces',
  place_id TEXT NOT NULL,
  place_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT saved_places_place_id_check CHECK (length(place_id) > 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS saved_places_trip_place_unique ON public.saved_places (trip_id, place_id);
CREATE INDEX IF NOT EXISTS saved_places_trip_idx ON public.saved_places (trip_id);
CREATE INDEX IF NOT EXISTS saved_places_user_idx ON public.saved_places (user_id);

-- inbound_webhook_receipts (audit trail; service_role write, admin read)
CREATE TABLE IF NOT EXISTS public.inbound_webhook_receipts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL CHECK (source IN ('stripe', 'qstash', 'supabase_outbound', 'other')),
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

-- search caches
CREATE TABLE IF NOT EXISTS public.search_destinations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  query TEXT NOT NULL,
  query_hash TEXT NOT NULL,
  results JSONB NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('google_maps','external_api','cached')),
  search_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.search_activities (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  destination TEXT NOT NULL,
  activity_type TEXT,
  query_parameters JSONB NOT NULL,
  query_hash TEXT NOT NULL,
  results JSONB NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('viator','getyourguide','googleplaces','ai_fallback','external_api','cached')),
  search_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.search_flights (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  origin TEXT NOT NULL,
  destination TEXT NOT NULL,
  departure_date DATE NOT NULL,
  return_date DATE,
  passengers INTEGER NOT NULL DEFAULT 1 CHECK (passengers > 0),
  cabin_class TEXT NOT NULL DEFAULT 'economy' CHECK (cabin_class IN ('economy','premium_economy','business','first')),
  query_parameters JSONB NOT NULL,
  query_hash TEXT NOT NULL,
  results JSONB NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('duffel','amadeus','external_api','cached')),
  search_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.search_hotels (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  destination TEXT NOT NULL,
  check_in_date DATE NOT NULL,
  check_out_date DATE NOT NULL,
  guests INTEGER NOT NULL DEFAULT 1 CHECK (guests > 0),
  rooms INTEGER NOT NULL DEFAULT 1 CHECK (rooms > 0),
  query_parameters JSONB NOT NULL,
  query_hash TEXT NOT NULL,
  results JSONB NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('amadeus','external_api','cached')),
  search_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT search_hotels_dates_check CHECK (check_out_date > check_in_date)
);

-- API Metrics table for dashboard metrics collection
CREATE TABLE IF NOT EXISTS public.api_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    duration_ms NUMERIC NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    error_type TEXT,
    rate_limit_key TEXT,
    CONSTRAINT api_metrics_status_code_check CHECK (status_code >= 100 AND status_code < 600),
    CONSTRAINT api_metrics_duration_ms_check CHECK (duration_ms >= 0),
    CONSTRAINT api_metrics_method_check CHECK (method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'))
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_api_metrics_created_at ON public.api_metrics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_metrics_endpoint ON public.api_metrics(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_metrics_user_id ON public.api_metrics(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_api_metrics_status_code ON public.api_metrics(status_code);
CREATE INDEX IF NOT EXISTS idx_api_metrics_time_status ON public.api_metrics(created_at DESC, status_code);

ALTER TABLE public.api_metrics ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "admin_read_api_metrics" ON public.api_metrics;
CREATE POLICY "admin_read_api_metrics" ON public.api_metrics
    FOR SELECT
    USING (
        auth.role() = 'authenticated'
        AND EXISTS (
            SELECT 1 FROM public.profiles
            WHERE profiles.id = auth.uid()
            AND profiles.is_admin = true
        )
    );

DROP POLICY IF EXISTS "service_role_all_api_metrics" ON public.api_metrics;
CREATE POLICY "service_role_all_api_metrics" ON public.api_metrics
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Data retention (90-day policy)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        IF NOT EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'cleanup_api_metrics_90d') THEN
            PERFORM cron.schedule(
                'cleanup_api_metrics_90d',
                '0 3 * * *',
                $cron$DELETE FROM public.api_metrics WHERE created_at < NOW() - INTERVAL '90 days'$cron$
            );
        END IF;
    END IF;
END;
$$;

-- Data retention for search caches (expire rows daily)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        IF NOT EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'cleanup_search_caches_daily') THEN
            PERFORM cron.schedule(
                'cleanup_search_caches_daily',
                '15 3 * * *',
                $cron$
                  DELETE FROM public.search_destinations WHERE expires_at < now();
                  DELETE FROM public.search_activities WHERE expires_at < now();
                  DELETE FROM public.search_flights WHERE expires_at < now();
                  DELETE FROM public.search_hotels WHERE expires_at < now();
                $cron$
            );
        END IF;
    END IF;
END;
$$;

-- Data retention for memories (interval configurable via MEMORIES_RETENTION_DAYS)
DO $$
DECLARE
    v_retention_days integer := COALESCE(
        NULLIF(current_setting('MEMORIES_RETENTION_DAYS', true), '')::integer,
        180
    );
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        IF NOT EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'cleanup_memories_180d') THEN
            PERFORM cron.schedule(
                'cleanup_memories_180d',
                '45 3 * * *',
                format(
                    $fmt$
                      DELETE FROM memories.turn_embeddings WHERE created_at < now() - interval '%s days';
                      DELETE FROM memories.turns WHERE created_at < now() - interval '%s days';
                      DELETE FROM memories.sessions WHERE created_at < now() - interval '%s days';
                    $fmt$,
                    v_retention_days,
                    v_retention_days,
                    v_retention_days
                )
            );
        END IF;
    END IF;
END;
$$;

COMMENT ON TABLE public.api_metrics IS 'API request metrics for dashboard analytics and observability';
COMMENT ON COLUMN public.api_metrics.endpoint IS 'API route pathname (e.g., /api/dashboard)';
COMMENT ON COLUMN public.api_metrics.method IS 'HTTP method (GET, POST, PUT, PATCH, DELETE)';
COMMENT ON COLUMN public.api_metrics.status_code IS 'HTTP response status code';
COMMENT ON COLUMN public.api_metrics.duration_ms IS 'Request duration in milliseconds';
COMMENT ON COLUMN public.api_metrics.user_id IS 'Authenticated user ID (null for anonymous requests)';
COMMENT ON COLUMN public.api_metrics.error_type IS 'Error class name for failed requests';
COMMENT ON COLUMN public.api_metrics.rate_limit_key IS 'Rate limit key used for this request';

-- webhook configuration and delivery logs
CREATE TABLE IF NOT EXISTS public.webhook_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  secret TEXT,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.webhook_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  config_id UUID REFERENCES public.webhook_configs(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  delivery_status TEXT NOT NULL DEFAULT 'pending' CHECK (delivery_status IN ('pending','delivered','failed','skipped')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at TIMESTAMPTZ,
  last_error TEXT
);

ALTER TABLE public.webhook_events
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.webhook_logs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id UUID REFERENCES public.webhook_events(id) ON DELETE CASCADE,
  attempt_number INTEGER NOT NULL DEFAULT 1,
  status_code INTEGER,
  response_body TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===========================
-- INDEXES
-- ===========================

-- Trips & collaboration
CREATE INDEX IF NOT EXISTS trips_user_dates_idx ON public.trips (user_id, start_date, end_date);
CREATE INDEX IF NOT EXISTS trips_status_idx ON public.trips (status);
CREATE INDEX IF NOT EXISTS trip_collaborators_trip_idx ON public.trip_collaborators (trip_id);
CREATE INDEX IF NOT EXISTS trip_collaborators_user_idx ON public.trip_collaborators (user_id);

-- Chat
CREATE INDEX IF NOT EXISTS chat_sessions_user_trip_idx ON public.chat_sessions (user_id, trip_id);
CREATE INDEX IF NOT EXISTS chat_messages_session_created_idx ON public.chat_messages (session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS chat_tool_calls_message_idx ON public.chat_tool_calls (message_id);

-- Itinerary / bookings
CREATE INDEX IF NOT EXISTS itinerary_items_trip_start_idx ON public.itinerary_items (trip_id, start_time);
CREATE INDEX IF NOT EXISTS flights_user_date_idx ON public.flights (user_id, departure_date);
CREATE INDEX IF NOT EXISTS accommodations_trip_dates_idx ON public.accommodations (trip_id, check_in_date, check_out_date);
CREATE INDEX IF NOT EXISTS bookings_user_status_idx ON public.bookings (user_id, status);

-- Search caches
CREATE INDEX IF NOT EXISTS search_destinations_hash_idx ON public.search_destinations (query_hash);
CREATE INDEX IF NOT EXISTS search_destinations_expires_idx ON public.search_destinations (expires_at);
CREATE INDEX IF NOT EXISTS search_activities_hash_idx ON public.search_activities (query_hash);
CREATE INDEX IF NOT EXISTS search_activities_expires_idx ON public.search_activities (expires_at);
CREATE INDEX IF NOT EXISTS search_flights_hash_idx ON public.search_flights (query_hash);
CREATE INDEX IF NOT EXISTS search_flights_expires_idx ON public.search_flights (expires_at);
CREATE INDEX IF NOT EXISTS search_hotels_hash_idx ON public.search_hotels (query_hash);
CREATE INDEX IF NOT EXISTS search_hotels_expires_idx ON public.search_hotels (expires_at);
CREATE INDEX IF NOT EXISTS search_hotels_user_created_idx ON public.search_hotels (user_id, created_at DESC);

-- Files & storage
CREATE UNIQUE INDEX IF NOT EXISTS file_attachments_path_idx ON public.file_attachments (file_path);
CREATE INDEX IF NOT EXISTS file_attachments_user_idx ON public.file_attachments (user_id);
CREATE INDEX IF NOT EXISTS file_attachments_trip_idx ON public.file_attachments (trip_id);
CREATE INDEX IF NOT EXISTS file_processing_queue_status_sched_idx ON public.file_processing_queue (status, scheduled_at);
CREATE INDEX IF NOT EXISTS file_versions_attachment_idx ON public.file_versions (file_attachment_id, is_current);

-- Memory (memories schema)
CREATE INDEX IF NOT EXISTS memories_sessions_user_idx ON memories.sessions (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS memories_turns_session_idx ON memories.turns (session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS memories_turns_user_idx ON memories.turns (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS memories_turn_embeddings_created_idx ON memories.turn_embeddings (created_at DESC);
DO $$
DECLARE
  v_hnsw_m integer := COALESCE(NULLIF(current_setting('PGVECTOR_HNSW_M', true), '')::integer, 32);
  v_hnsw_ef_construction integer := COALESCE(
    NULLIF(current_setting('PGVECTOR_HNSW_EF_CONSTRUCTION', true), '')::integer,
    180
  );
BEGIN
  EXECUTE format(
    'CREATE INDEX IF NOT EXISTS memories_turn_embeddings_vector_idx ON memories.turn_embeddings USING hnsw (embedding vector_l2_ops) WITH (m = %s, ef_construction = %s);',
    v_hnsw_m,
    v_hnsw_ef_construction
  );
END;
$$;

-- BYOK / settings
CREATE INDEX IF NOT EXISTS api_gateway_configs_user_idx ON public.api_gateway_configs (user_id);
CREATE INDEX IF NOT EXISTS user_settings_user_idx ON public.user_settings (user_id);
CREATE INDEX IF NOT EXISTS webhook_configs_enabled_idx ON public.webhook_configs (enabled);
CREATE INDEX IF NOT EXISTS webhook_events_status_idx ON public.webhook_events (delivery_status, created_at DESC);
CREATE INDEX IF NOT EXISTS webhook_logs_event_idx ON public.webhook_logs (event_id);

-- ===========================
-- FUNCTIONS & TRIGGERS
-- ===========================

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Vault-backed API key helpers (service_role only)
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

-- Gateway config + consent helpers (service_role only)
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
    RETURN TRUE;
  END IF;
  RETURN v_flag;
END; $$;

-- Admin flag helper
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
  SELECT coalesce(
    nullif(current_setting('request.jwt.claims', true)::json -> 'app_metadata' ->> 'is_admin', ''),
    nullif(current_setting('request.jwt.claims', true)::json ->> 'is_admin', '')
  ) = 'true';
$$;

-- Agent configuration (active + versions)
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

-- Seed baseline agent configuration (idempotent)
DO $$
DECLARE
  agents constant text[] := array[
    'budgetAgent',
    'destinationResearchAgent',
    'itineraryAgent',
    'flightAgent',
    'accommodationAgent',
    'memoryAgent'
  ];
  agent text;
  version_id uuid;
  cfg jsonb;
BEGIN
  FOREACH agent IN ARRAY agents LOOP
    cfg := jsonb_build_object(
      'agentType', agent,
      'createdAt', to_char(now(), 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
      'updatedAt', to_char(now(), 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
      'id', concat('v', extract(epoch from now())::bigint, '_', substr(md5(agent), 1, 8)),
      'model', 'gpt-4o',
      'parameters', jsonb_build_object(
        'temperature', 0.3,
        'maxOutputTokens', 4096,
        'topP', 0.9
      ),
      'scope', 'global'
    );

    INSERT INTO public.agent_config_versions(agent_type, scope, config, summary)
    VALUES (agent, 'global', cfg, 'seed')
    ON CONFLICT DO NOTHING
    RETURNING id INTO version_id;

    IF version_id IS NULL THEN
      SELECT id INTO version_id FROM public.agent_config_versions
      WHERE agent_type = agent AND scope = 'global'
      ORDER BY created_at DESC LIMIT 1;
    END IF;

    INSERT INTO public.agent_config(agent_type, scope, config, version_id)
    VALUES (agent, 'global', cfg, version_id)
    ON CONFLICT (agent_type, scope) DO UPDATE SET
      config = EXCLUDED.config,
      version_id = EXCLUDED.version_id,
      updated_at = now();
  END LOOP;
END$$;

-- Normalize legacy agent config parameter keys (maxTokens/maxSteps -> maxOutputTokens/stepLimit)
UPDATE public.agent_config
SET config = jsonb_set(
  config,
  '{parameters}',
  jsonb_strip_nulls(
    (
      COALESCE(config->'parameters', '{}'::jsonb)
      - 'maxTokens'
      - 'maxSteps'
    ) || jsonb_build_object(
      'maxOutputTokens',
      COALESCE(config->'parameters'->'maxOutputTokens', config->'parameters'->'maxTokens'),
      'stepLimit',
      COALESCE(config->'parameters'->'stepLimit', config->'parameters'->'maxSteps')
    )
  ),
  true
)
WHERE (config->'parameters' ? 'maxTokens') OR (config->'parameters' ? 'maxSteps');

UPDATE public.agent_config_versions
SET config = jsonb_set(
  config,
  '{parameters}',
  jsonb_strip_nulls(
    (
      COALESCE(config->'parameters', '{}'::jsonb)
      - 'maxTokens'
      - 'maxSteps'
    ) || jsonb_build_object(
      'maxOutputTokens',
      COALESCE(config->'parameters'->'maxOutputTokens', config->'parameters'->'maxTokens'),
      'stepLimit',
      COALESCE(config->'parameters'->'stepLimit', config->'parameters'->'maxSteps')
    )
  ),
  true
)
WHERE (config->'parameters' ? 'maxTokens') OR (config->'parameters' ? 'maxSteps');

-- Normalize legacy agent config IDs to match versionId schema (v{epoch}_{hash})
UPDATE public.agent_config
SET config = jsonb_set(
  config,
  '{id}',
  to_jsonb(
    concat(
      'v',
      extract(epoch from created_at)::bigint,
      '_',
      substr(md5(version_id::text), 1, 8)
    )
  ),
  true
)
WHERE (config->>'id') IS NULL OR NOT (config->>'id') ~ '^v\\d+_[a-f0-9]{8}$';

UPDATE public.agent_config_versions
SET config = jsonb_set(
  config,
  '{id}',
  to_jsonb(
    concat(
      'v',
      extract(epoch from created_at)::bigint,
      '_',
      substr(md5(id::text), 1, 8)
    )
  ),
  true
)
WHERE (config->>'id') IS NULL OR NOT (config->>'id') ~ '^v\\d+_[a-f0-9]{8}$';

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
  v_config jsonb;
BEGIN
  INSERT INTO public.agent_config_versions(agent_type, scope, config, created_by, summary)
  VALUES (p_agent_type, p_scope, p_config, p_created_by, p_summary)
  RETURNING agent_config_versions.id, agent_config_versions.config INTO v_version_id, v_config;

  INSERT INTO public.agent_config(agent_type, scope, config, version_id)
  VALUES (p_agent_type, p_scope, p_config, v_version_id)
  ON CONFLICT (agent_type, scope)
  DO UPDATE SET
    config = EXCLUDED.config,
    version_id = v_version_id,
    updated_at = now();

  RETURN QUERY SELECT v_version_id, v_config;
END;
$$;

CREATE OR REPLACE FUNCTION public.match_accommodation_embeddings (
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.75,
  match_count INT DEFAULT 20,
  ef_search_override INT DEFAULT NULL
)
RETURNS TABLE (id TEXT, similarity FLOAT)
LANGUAGE plpgsql AS $$
DECLARE
  v_ef_search integer := COALESCE(
    ef_search_override,
    NULLIF(current_setting('PGVECTOR_HNSW_EF_SEARCH_DEFAULT', true), '')::integer,
    96
  );
BEGIN
  PERFORM set_config('hnsw.ef_search', v_ef_search::text, true);
  RETURN QUERY
  SELECT accom.id, 1 - (accom.embedding <=> query_embedding) AS similarity
  FROM public.accommodation_embeddings accom
  WHERE 1 - (accom.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;

-- Trip collaboration helpers (SECURITY DEFINER to avoid RLS recursion)
CREATE OR REPLACE FUNCTION public.user_has_trip_access(p_user_id UUID, p_trip_id BIGINT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public, pg_temp
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM public.trips t
    WHERE t.id = p_trip_id
      AND t.user_id = p_user_id
    UNION
    SELECT 1
    FROM public.trip_collaborators tc
    WHERE tc.trip_id = p_trip_id
      AND tc.user_id = p_user_id
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.user_is_trip_owner(p_user_id UUID, p_trip_id BIGINT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public, pg_temp
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM public.trips t
    WHERE t.id = p_trip_id
      AND t.user_id = p_user_id
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.user_has_trip_edit_access(p_user_id UUID, p_trip_id BIGINT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public, pg_temp
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM public.trips t
    WHERE t.id = p_trip_id
      AND t.user_id = p_user_id
    UNION
    SELECT 1
    FROM public.trip_collaborators tc
    WHERE tc.trip_id = p_trip_id
      AND tc.user_id = p_user_id
      AND tc.role IN ('editor', 'admin')
  );
END;
$$;

-- Storage path parsing helper (defense in depth; returns NULL when unmatched).
CREATE OR REPLACE FUNCTION public.extract_trip_id_from_path(file_path TEXT)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public, pg_temp
AS $$
DECLARE trip_id_text TEXT;
BEGIN
  trip_id_text := substring(file_path from 'trip[s]?[_/](\\d+)');
  IF trip_id_text IS NULL THEN
    RETURN NULL;
  END IF;
  RETURN trip_id_text::BIGINT;
EXCEPTION
  WHEN OTHERS THEN
    RETURN NULL;
END;
$$;

-- Collaborator helper RPCs (service-role only)
CREATE OR REPLACE FUNCTION public.auth_user_id_by_email(p_email TEXT)
RETURNS UUID
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = auth, public, pg_temp
AS $$
  SELECT u.id
  FROM auth.users u
  WHERE lower(u.email) = lower(p_email)
  LIMIT 1;
$$;

REVOKE ALL ON FUNCTION public.auth_user_id_by_email(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.auth_user_id_by_email(TEXT) TO service_role;

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

-- RAG search functions (SECURITY INVOKER; RLS remains in effect)
CREATE OR REPLACE FUNCTION public.match_rag_documents (
  query_embedding vector(1536),
  filter_namespace TEXT DEFAULT NULL,
  match_threshold FLOAT DEFAULT 0.0,
  match_count INT DEFAULT 10
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  namespace TEXT,
  source_id TEXT,
  chunk_index INT,
  similarity FLOAT
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_ef_search integer := COALESCE(
    NULLIF(current_setting('PGVECTOR_HNSW_EF_SEARCH_DEFAULT', true), '')::integer,
    96
  );
BEGIN
  PERFORM set_config('hnsw.ef_search', v_ef_search::text, true);
  RETURN QUERY
  SELECT
    d.id,
    d.content,
    d.metadata,
    d.namespace,
    d.source_id,
    d.chunk_index,
    1 - (d.embedding OPERATOR(extensions.<=>) query_embedding) AS similarity
  FROM public.rag_documents d
  WHERE
    (filter_namespace IS NULL OR d.namespace = filter_namespace)
    AND 1 - (d.embedding OPERATOR(extensions.<=>) query_embedding) > match_threshold
  ORDER BY d.embedding OPERATOR(extensions.<=>) query_embedding
  LIMIT match_count;
END;
$$;

CREATE OR REPLACE FUNCTION public.hybrid_rag_search (
  query_text TEXT,
  query_embedding vector(1536),
  filter_namespace TEXT DEFAULT NULL,
  match_count INT DEFAULT 10,
  match_threshold FLOAT DEFAULT 0.0,
  keyword_weight FLOAT DEFAULT 0.3,
  semantic_weight FLOAT DEFAULT 0.7
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  namespace TEXT,
  source_id TEXT,
  chunk_index INT,
  similarity FLOAT,
  keyword_rank FLOAT,
  combined_score FLOAT
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_ef_search integer := COALESCE(
    NULLIF(current_setting('PGVECTOR_HNSW_EF_SEARCH_DEFAULT', true), '')::integer,
    96
  );
BEGIN
  PERFORM set_config('hnsw.ef_search', v_ef_search::text, true);
  RETURN QUERY
  WITH semantic_results AS (
    SELECT
      d.id,
      d.content,
      d.metadata,
      d.namespace,
      d.source_id,
      d.chunk_index,
      1 - (d.embedding OPERATOR(extensions.<=>) query_embedding) AS sim_score
    FROM public.rag_documents d
    WHERE
      (filter_namespace IS NULL OR d.namespace = filter_namespace)
      AND 1 - (d.embedding OPERATOR(extensions.<=>) query_embedding) > match_threshold
    ORDER BY d.embedding OPERATOR(extensions.<=>) query_embedding
    LIMIT match_count * 2
  ),
    keyword_results AS (
      SELECT
        d.id,
        ts_rank_cd(d.fts, websearch_to_tsquery('english', query_text), 32) AS kw_rank
      FROM public.rag_documents d
      WHERE
        (filter_namespace IS NULL OR d.namespace = filter_namespace)
        AND d.fts @@ websearch_to_tsquery('english', query_text)
      ORDER BY kw_rank DESC
      LIMIT match_count * 2
    )
  SELECT
    s.id,
    s.content,
    s.metadata,
    s.namespace,
    s.source_id,
    s.chunk_index,
    s.sim_score AS similarity,
    COALESCE(k.kw_rank, 0::FLOAT) AS keyword_rank,
    (s.sim_score * semantic_weight + COALESCE(k.kw_rank, 0::FLOAT) * keyword_weight) AS combined_score
  FROM semantic_results s
  LEFT JOIN keyword_results k ON s.id = k.id
  ORDER BY combined_score DESC
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION public.match_rag_documents IS 'Performs pure semantic search using vector similarity.';
COMMENT ON FUNCTION public.hybrid_rag_search IS 'Performs hybrid search combining vector similarity and full-text matching.';

REVOKE EXECUTE ON FUNCTION public.match_rag_documents(
  extensions.vector(1536),
  text,
  double precision,
  integer
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.match_rag_documents(
  extensions.vector(1536),
  text,
  double precision,
  integer
) TO authenticated, service_role;

REVOKE EXECUTE ON FUNCTION public.hybrid_rag_search(
  text,
  extensions.vector(1536),
  text,
  integer,
  double precision,
  double precision,
  double precision
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.hybrid_rag_search(
  text,
  extensions.vector(1536),
  text,
  integer,
  double precision,
  double precision,
  double precision
) TO authenticated, service_role;

-- Memory semantic search (turn embeddings)
CREATE OR REPLACE FUNCTION memories.match_turn_embeddings(
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 10,
  filter_user_id UUID DEFAULT NULL,
  filter_session_id UUID DEFAULT NULL,
  ef_search_override INT DEFAULT NULL
)
RETURNS TABLE (
  turn_id UUID,
  session_id UUID,
  user_id UUID,
  content JSONB,
  role TEXT,
  similarity FLOAT,
  created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_jwt_role text := COALESCE(auth.jwt() ->> 'role', '');
  v_auth_uid uuid := auth.uid();
  v_effective_user_id uuid;
  v_ef_search integer := COALESCE(
    ef_search_override,
    NULLIF(current_setting('PGVECTOR_HNSW_EF_SEARCH_DEFAULT', true), '')::integer,
    96
  );
BEGIN
  IF v_auth_uid IS NOT NULL THEN
    IF filter_user_id IS NULL THEN
      v_effective_user_id := v_auth_uid;
    ELSIF filter_user_id <> v_auth_uid THEN
      RAISE EXCEPTION 'filter_user_id must match authenticated user'
        USING ERRCODE = '42501';
    ELSE
      v_effective_user_id := filter_user_id;
    END IF;
  ELSE
    IF v_jwt_role = 'service_role' THEN
      IF filter_user_id IS NULL THEN
        RAISE EXCEPTION 'filter_user_id is required for service_role calls'
          USING ERRCODE = '22023';
      END IF;
      v_effective_user_id := filter_user_id;
    ELSE
      RAISE EXCEPTION 'authentication required'
        USING ERRCODE = '28000';
    END IF;
  END IF;

  IF match_count <= 0 THEN
    RAISE EXCEPTION 'match_count must be > 0'
      USING ERRCODE = '22023';
  END IF;

  IF match_threshold < 0 OR match_threshold > 1 THEN
    RAISE EXCEPTION 'match_threshold must be between 0 and 1'
      USING ERRCODE = '22023';
  END IF;

  IF ef_search_override IS NOT NULL AND (ef_search_override < 1 OR ef_search_override > 1000) THEN
    RAISE EXCEPTION 'ef_search_override must be between 1 and 1000'
      USING ERRCODE = '22023';
  END IF;

  PERFORM set_config('hnsw.ef_search', v_ef_search::text, true);

  RETURN QUERY
  SELECT
    te.turn_id,
    t.session_id,
    t.user_id,
    t.content,
    t.role,
    1 - (te.embedding OPERATOR(extensions.<=>) query_embedding) AS similarity,
    t.created_at
  FROM memories.turn_embeddings te
  JOIN memories.turns t ON t.id = te.turn_id
  WHERE
    t.user_id = v_effective_user_id
    AND (filter_session_id IS NULL OR t.session_id = filter_session_id)
    AND 1 - (te.embedding OPERATOR(extensions.<=>) query_embedding) > match_threshold
  ORDER BY te.embedding OPERATOR(extensions.<=>) query_embedding
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION memories.match_turn_embeddings IS
  'Performs semantic search on memory turn embeddings using 1536-d pgvector (text-embedding-3-small). '
  'Returns turns matching the query embedding above the similarity threshold, ordered by relevance.';

REVOKE EXECUTE ON FUNCTION memories.match_turn_embeddings(
  extensions.vector(1536),
  double precision,
  integer,
  uuid,
  uuid,
  integer
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memories.match_turn_embeddings(
  extensions.vector(1536),
  double precision,
  integer,
  uuid,
  uuid,
  integer
) TO authenticated, service_role;

-- Atomic deletion of user memories (service_role only)
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

REVOKE ALL ON FUNCTION public.delete_user_memories(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.delete_user_memories(UUID) TO service_role;

-- Realtime helpers
CREATE OR REPLACE FUNCTION public.rt_topic_prefix()
RETURNS text
LANGUAGE sql STABLE AS $$ select split_part(realtime.topic(), ':', 1) $$;

CREATE OR REPLACE FUNCTION public.rt_topic_suffix()
RETURNS text
LANGUAGE sql STABLE AS $$ select split_part(realtime.topic(), ':', 2) $$;

CREATE OR REPLACE FUNCTION public.try_cast_uuid(p_value TEXT)
RETURNS UUID
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  RETURN p_value::uuid;
EXCEPTION
  WHEN OTHERS THEN
    RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION public.try_cast_bigint(p_value TEXT)
RETURNS BIGINT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  RETURN p_value::bigint;
EXCEPTION
  WHEN OTHERS THEN
    RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION public.rt_is_session_member()
RETURNS boolean
LANGUAGE plpgsql
STABLE AS $$
DECLARE ok boolean := false;
DECLARE session_id uuid;
BEGIN
  IF to_regclass('public.chat_sessions') IS NULL THEN
    RETURN false;
  END IF;

  session_id := public.try_cast_uuid(public.rt_topic_suffix());
  IF session_id IS NULL THEN
    RETURN false;
  END IF;

  EXECUTE '
    SELECT EXISTS (
      SELECT 1
      FROM public.chat_sessions cs
      LEFT JOIN public.trips t ON t.id = cs.trip_id
      LEFT JOIN public.trip_collaborators tc ON tc.trip_id = cs.trip_id AND tc.user_id = auth.uid()
      WHERE cs.id = $1
        AND (cs.user_id = auth.uid() OR t.user_id = auth.uid() OR tc.user_id IS NOT NULL)
    )'
    INTO ok
    USING session_id;

  RETURN ok;
END;
$$;

-- Collaboration invariants (defense in depth)
CREATE OR REPLACE FUNCTION public.prevent_itinerary_user_id_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.user_id IS DISTINCT FROM OLD.user_id THEN
    RAISE EXCEPTION 'user_id cannot be modified';
  END IF;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.prevent_saved_places_identity_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.user_id IS DISTINCT FROM OLD.user_id THEN
    RAISE EXCEPTION 'user_id cannot be modified';
  END IF;
  IF NEW.trip_id IS DISTINCT FROM OLD.trip_id THEN
    RAISE EXCEPTION 'trip_id cannot be modified';
  END IF;
  IF NEW.place_id IS DISTINCT FROM OLD.place_id THEN
    RAISE EXCEPTION 'place_id cannot be modified';
  END IF;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.prevent_file_attachments_identity_change()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  IF session_user IN ('postgres', 'supabase_admin') OR auth.role() = 'service_role' THEN
    RETURN NEW;
  END IF;

  IF NEW.file_path IS DISTINCT FROM OLD.file_path THEN
    RAISE EXCEPTION 'file_path cannot be modified';
  END IF;
  IF NEW.user_id IS DISTINCT FROM OLD.user_id THEN
    RAISE EXCEPTION 'user_id cannot be modified';
  END IF;
  IF NEW.bucket_name IS DISTINCT FROM OLD.bucket_name THEN
    RAISE EXCEPTION 'bucket_name cannot be modified';
  END IF;

  RETURN NEW;
END;
$$;

-- Triggers: updated_at
DO $$
BEGIN
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_trips_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_trips_updated_at BEFORE UPDATE ON public.trips
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_itinerary_items_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_itinerary_items_updated_at BEFORE UPDATE ON public.itinerary_items
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_bookings_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_bookings_updated_at BEFORE UPDATE ON public.bookings
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_chat_sessions_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_chat_sessions_updated_at BEFORE UPDATE ON public.chat_sessions
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_file_attachments_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_file_attachments_updated_at BEFORE UPDATE ON public.file_attachments
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_rag_documents_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_rag_documents_updated_at BEFORE UPDATE ON public.rag_documents
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_saved_places_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_saved_places_updated_at BEFORE UPDATE ON public.saved_places
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_agent_config_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_agent_config_updated_at BEFORE UPDATE ON public.agent_config
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_profiles_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_profiles_updated_at BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_webhook_configs_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_webhook_configs_updated_at BEFORE UPDATE ON public.webhook_configs
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_webhook_events_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_webhook_events_updated_at BEFORE UPDATE ON public.webhook_events
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_memories_sessions_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_memories_sessions_updated_at BEFORE UPDATE ON memories.sessions
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_memories_turns_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_memories_turns_updated_at BEFORE UPDATE ON memories.turns
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
END$$;

-- Triggers: invariants
DROP TRIGGER IF EXISTS itinerary_items_prevent_user_id_change ON public.itinerary_items;
CREATE TRIGGER itinerary_items_prevent_user_id_change
  BEFORE UPDATE ON public.itinerary_items
  FOR EACH ROW EXECUTE FUNCTION public.prevent_itinerary_user_id_change();

DROP TRIGGER IF EXISTS saved_places_prevent_identity_change ON public.saved_places;
CREATE TRIGGER saved_places_prevent_identity_change
  BEFORE UPDATE ON public.saved_places
  FOR EACH ROW EXECUTE FUNCTION public.prevent_saved_places_identity_change();

DROP TRIGGER IF EXISTS file_attachments_prevent_identity_change ON public.file_attachments;
CREATE TRIGGER file_attachments_prevent_identity_change
  BEFORE UPDATE ON public.file_attachments
  FOR EACH ROW EXECUTE FUNCTION public.prevent_file_attachments_identity_change();

-- ===========================
-- RLS POLICIES
-- ===========================

ALTER TABLE public.trips ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "trips_insert_own" ON public.trips;
CREATE POLICY trips_insert_own ON public.trips FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "trips_select_own" ON public.trips;
DROP POLICY IF EXISTS trips_select_accessible ON public.trips;
CREATE POLICY trips_select_accessible
  ON public.trips
  FOR SELECT
  TO authenticated
  USING (public.user_has_trip_access((select auth.uid()), id));

DROP POLICY IF EXISTS "trips_update_own" ON public.trips;
DROP POLICY IF EXISTS trips_update_collaborators ON public.trips;
CREATE POLICY trips_update_collaborators
  ON public.trips
  FOR UPDATE
  TO authenticated
  USING (public.user_has_trip_edit_access((select auth.uid()), id))
  WITH CHECK (public.user_has_trip_edit_access((select auth.uid()), id));
DROP POLICY IF EXISTS "trips_delete_own" ON public.trips;
CREATE POLICY trips_delete_own ON public.trips FOR DELETE TO authenticated USING (auth.uid() = user_id);

ALTER TABLE public.trip_collaborators ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "trip_collab_select" ON public.trip_collaborators;
DROP POLICY IF EXISTS "trip_collab_insert" ON public.trip_collaborators;
DROP POLICY IF EXISTS trip_collaborators_select_trip_members ON public.trip_collaborators;
DROP POLICY IF EXISTS trip_collaborators_insert_owner ON public.trip_collaborators;
DROP POLICY IF EXISTS trip_collaborators_update_owner ON public.trip_collaborators;
DROP POLICY IF EXISTS trip_collaborators_delete_owner_or_self ON public.trip_collaborators;
DROP POLICY IF EXISTS trip_collaborators_service_all ON public.trip_collaborators;

CREATE POLICY trip_collaborators_select_trip_members
  ON public.trip_collaborators
  FOR SELECT
  TO authenticated
  USING (public.user_has_trip_access((select auth.uid()), trip_id));

CREATE POLICY trip_collaborators_insert_owner
  ON public.trip_collaborators
  FOR INSERT
  TO authenticated
  WITH CHECK (public.user_is_trip_owner((select auth.uid()), trip_id));

CREATE POLICY trip_collaborators_update_owner
  ON public.trip_collaborators
  FOR UPDATE
  TO authenticated
  USING (public.user_is_trip_owner((select auth.uid()), trip_id))
  WITH CHECK (public.user_is_trip_owner((select auth.uid()), trip_id));

CREATE POLICY trip_collaborators_delete_owner_or_self
  ON public.trip_collaborators
  FOR DELETE
  TO authenticated
  USING (public.user_is_trip_owner((select auth.uid()), trip_id) OR user_id = (select auth.uid()));

CREATE POLICY trip_collaborators_service_all
  ON public.trip_collaborators
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

ALTER TABLE public.flights ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "flights_select_own" ON public.flights;
CREATE POLICY flights_select_own ON public.flights FOR SELECT TO authenticated USING (user_id = auth.uid());
DROP POLICY IF EXISTS "flights_mutate_own" ON public.flights;
CREATE POLICY flights_mutate_own ON public.flights FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

ALTER TABLE public.bookings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "bookings_select_own" ON public.bookings;
CREATE POLICY bookings_select_own ON public.bookings FOR SELECT TO authenticated USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "bookings_insert_own" ON public.bookings;
CREATE POLICY bookings_insert_own ON public.bookings FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "bookings_update_own" ON public.bookings;
CREATE POLICY bookings_update_own ON public.bookings FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "bookings_all_service" ON public.bookings;
CREATE POLICY bookings_all_service ON public.bookings FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE public.accommodation_embeddings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "embeddings_select_auth" ON public.accommodation_embeddings;
CREATE POLICY embeddings_select_auth ON public.accommodation_embeddings FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS "embeddings_all_service" ON public.accommodation_embeddings;
CREATE POLICY embeddings_all_service ON public.accommodation_embeddings FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE public.itinerary_items ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "itinerary_select_own" ON public.itinerary_items;
DROP POLICY IF EXISTS "itinerary_insert_own" ON public.itinerary_items;
DROP POLICY IF EXISTS "itinerary_update_own" ON public.itinerary_items;
DROP POLICY IF EXISTS itinerary_delete_trip_edit ON public.itinerary_items;
DROP POLICY IF EXISTS itinerary_select_trip_access ON public.itinerary_items;
DROP POLICY IF EXISTS itinerary_insert_trip_edit ON public.itinerary_items;
DROP POLICY IF EXISTS itinerary_update_trip_edit ON public.itinerary_items;

CREATE POLICY itinerary_select_trip_access
  ON public.itinerary_items
  FOR SELECT
  TO authenticated
  USING (public.user_has_trip_access((select auth.uid()), trip_id));

CREATE POLICY itinerary_insert_trip_edit
  ON public.itinerary_items
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = (select auth.uid())
    AND public.user_has_trip_edit_access((select auth.uid()), trip_id)
  );

CREATE POLICY itinerary_update_trip_edit
  ON public.itinerary_items
  FOR UPDATE
  TO authenticated
  USING (public.user_has_trip_edit_access((select auth.uid()), trip_id))
  WITH CHECK (public.user_has_trip_edit_access((select auth.uid()), trip_id));

CREATE POLICY itinerary_delete_trip_edit
  ON public.itinerary_items
  FOR DELETE
  TO authenticated
  USING (public.user_has_trip_edit_access((select auth.uid()), trip_id));

ALTER TABLE public.accommodations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "accommodations_select_own" ON public.accommodations;
CREATE POLICY accommodations_select_own ON public.accommodations FOR SELECT TO authenticated USING (
  trip_id IN (SELECT id FROM public.trips WHERE user_id = auth.uid())
);
DROP POLICY IF EXISTS "accommodations_mutate_own" ON public.accommodations;
CREATE POLICY accommodations_mutate_own ON public.accommodations FOR ALL TO authenticated USING (
  trip_id IN (SELECT id FROM public.trips WHERE user_id = auth.uid())
) WITH CHECK (
  trip_id IN (SELECT id FROM public.trips WHERE user_id = auth.uid())
);

ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "chat_sessions_select" ON public.chat_sessions;
CREATE POLICY chat_sessions_select ON public.chat_sessions FOR SELECT TO authenticated USING (
  user_id = (select auth.uid())
  OR (
    trip_id IS NOT NULL
    AND public.user_has_trip_access((select auth.uid()), trip_id)
  )
);
DROP POLICY IF EXISTS "chat_sessions_insert" ON public.chat_sessions;
CREATE POLICY chat_sessions_insert
  ON public.chat_sessions
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = (select auth.uid())
    AND (
      trip_id IS NULL
      OR public.user_has_trip_access((select auth.uid()), trip_id)
    )
  );

DROP POLICY IF EXISTS chat_sessions_update_owner ON public.chat_sessions;
CREATE POLICY chat_sessions_update_owner
  ON public.chat_sessions
  FOR UPDATE
  TO authenticated
  USING (user_id = (select auth.uid()))
  WITH CHECK (user_id = (select auth.uid()));

DROP POLICY IF EXISTS chat_sessions_delete_owner ON public.chat_sessions;
CREATE POLICY chat_sessions_delete_owner
  ON public.chat_sessions
  FOR DELETE
  TO authenticated
  USING (user_id = (select auth.uid()));

ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "chat_messages_select" ON public.chat_messages;
CREATE POLICY chat_messages_select ON public.chat_messages FOR SELECT TO authenticated USING (
  session_id IN (
    SELECT id FROM public.chat_sessions
    WHERE user_id = auth.uid()
    OR trip_id IN (
      SELECT id FROM public.trips WHERE user_id = auth.uid()
      UNION
      SELECT trip_id FROM public.trip_collaborators WHERE user_id = auth.uid()
    )
  )
);
DROP POLICY IF EXISTS "chat_messages_insert" ON public.chat_messages;
CREATE POLICY chat_messages_insert ON public.chat_messages FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid() AND session_id IN (SELECT id FROM public.chat_sessions WHERE user_id = auth.uid()));

ALTER TABLE public.chat_tool_calls ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "chat_tool_calls_select" ON public.chat_tool_calls;
CREATE POLICY chat_tool_calls_select ON public.chat_tool_calls FOR SELECT TO authenticated USING (
  message_id IN (
    SELECT cm.id
    FROM public.chat_messages cm
    JOIN public.chat_sessions cs ON cm.session_id = cs.id
    WHERE cs.user_id = auth.uid()
    OR cs.trip_id IN (
      SELECT id FROM public.trips WHERE user_id = auth.uid()
      UNION
      SELECT trip_id FROM public.trip_collaborators WHERE user_id = auth.uid()
    )
  )
);
DROP POLICY IF EXISTS "chat_tool_calls_insert" ON public.chat_tool_calls;
CREATE POLICY chat_tool_calls_insert ON public.chat_tool_calls FOR INSERT TO authenticated WITH CHECK (
  message_id IN (
    SELECT id FROM public.chat_messages WHERE user_id = auth.uid()
  )
);

ALTER TABLE public.api_gateway_configs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "api_gateway_configs_owner" ON public.api_gateway_configs;
CREATE POLICY api_gateway_configs_owner ON public.api_gateway_configs FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "api_gateway_configs_service" ON public.api_gateway_configs;
CREATE POLICY api_gateway_configs_service ON public.api_gateway_configs FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_settings_owner" ON public.user_settings;
CREATE POLICY user_settings_owner ON public.user_settings FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "user_settings_service" ON public.user_settings;
CREATE POLICY user_settings_service ON public.user_settings FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "api_keys_owner" ON public.api_keys;
CREATE POLICY api_keys_owner ON public.api_keys FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "api_keys_service" ON public.api_keys;
CREATE POLICY api_keys_service ON public.api_keys FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE public.webhook_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.webhook_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.webhook_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "webhook_configs_service_all" ON public.webhook_configs;
CREATE POLICY webhook_configs_service_all ON public.webhook_configs FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "webhook_configs_admin_read" ON public.webhook_configs;
CREATE POLICY webhook_configs_admin_read ON public.webhook_configs FOR SELECT TO authenticated USING (public.is_admin());

DROP POLICY IF EXISTS "webhook_events_service_all" ON public.webhook_events;
CREATE POLICY webhook_events_service_all ON public.webhook_events FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "webhook_events_admin_read" ON public.webhook_events;
CREATE POLICY webhook_events_admin_read ON public.webhook_events FOR SELECT TO authenticated USING (public.is_admin());

DROP POLICY IF EXISTS "webhook_logs_service_all" ON public.webhook_logs;
CREATE POLICY webhook_logs_service_all ON public.webhook_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "webhook_logs_admin_read" ON public.webhook_logs;
CREATE POLICY webhook_logs_admin_read ON public.webhook_logs FOR SELECT TO authenticated USING (public.is_admin());

ALTER TABLE public.file_attachments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS file_attachments_owner ON public.file_attachments;
DROP POLICY IF EXISTS file_attachments_select_access ON public.file_attachments;
DROP POLICY IF EXISTS file_attachments_insert_owner ON public.file_attachments;
DROP POLICY IF EXISTS file_attachments_update_owner ON public.file_attachments;
DROP POLICY IF EXISTS file_attachments_delete_owner ON public.file_attachments;
DROP POLICY IF EXISTS file_attachments_service ON public.file_attachments;

CREATE POLICY file_attachments_select_access
  ON public.file_attachments
  FOR SELECT
  TO authenticated
  USING (
    user_id = (select auth.uid())
    OR (
      trip_id IS NOT NULL
      AND public.user_has_trip_access((select auth.uid()), trip_id)
    )
  );

CREATE POLICY file_attachments_insert_owner
  ON public.file_attachments
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = (select auth.uid())
    AND (
      split_part(file_path, '/', 1) = (select auth.uid())::text
      OR (
        split_part(file_path, '/', 1) = 'chat'
        AND split_part(file_path, '/', 2) = (select auth.uid())::text
      )
    )
    AND (
      trip_id IS NULL
      OR public.user_has_trip_edit_access((select auth.uid()), trip_id)
    )
    AND (
      chat_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM public.chat_sessions cs
        WHERE cs.id = chat_id
          AND cs.user_id = (select auth.uid())
      )
    )
    AND (
      chat_message_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM public.chat_messages cm
        WHERE cm.id = chat_message_id
          AND cm.user_id = (select auth.uid())
      )
    )
  );

CREATE POLICY file_attachments_update_owner
  ON public.file_attachments
  FOR UPDATE
  TO authenticated
  USING (user_id = (select auth.uid()))
  WITH CHECK (
    user_id = (select auth.uid())
    AND (
      split_part(file_path, '/', 1) = (select auth.uid())::text
      OR (
        split_part(file_path, '/', 1) = 'chat'
        AND split_part(file_path, '/', 2) = (select auth.uid())::text
      )
    )
    AND (
      trip_id IS NULL
      OR public.user_has_trip_edit_access((select auth.uid()), trip_id)
    )
    AND (
      chat_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM public.chat_sessions cs
        WHERE cs.id = chat_id
          AND cs.user_id = (select auth.uid())
      )
    )
    AND (
      chat_message_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM public.chat_messages cm
        WHERE cm.id = chat_message_id
          AND cm.user_id = (select auth.uid())
      )
    )
  );

CREATE POLICY file_attachments_delete_owner
  ON public.file_attachments
  FOR DELETE
  TO authenticated
  USING (user_id = (select auth.uid()));

CREATE POLICY file_attachments_service
  ON public.file_attachments
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

ALTER TABLE public.rag_documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow authenticated users to read RAG documents" ON public.rag_documents;
DROP POLICY IF EXISTS "Allow anonymous users to read RAG documents" ON public.rag_documents;
DROP POLICY IF EXISTS "Allow service role to manage RAG documents" ON public.rag_documents;
DROP POLICY IF EXISTS rag_documents_select_authenticated ON public.rag_documents;
DROP POLICY IF EXISTS rag_documents_insert_authenticated ON public.rag_documents;
DROP POLICY IF EXISTS rag_documents_update_authenticated ON public.rag_documents;
DROP POLICY IF EXISTS rag_documents_delete_authenticated ON public.rag_documents;
DROP POLICY IF EXISTS rag_documents_service_all ON public.rag_documents;

CREATE POLICY rag_documents_select_authenticated
  ON public.rag_documents
  FOR SELECT
  TO authenticated
  USING (
    (
      user_id IS NULL
      AND namespace IN ('default', 'accommodations', 'destinations', 'activities', 'travel_tips')
    )
    OR user_id = (select auth.uid())
    OR (
      trip_id IS NOT NULL
      AND public.user_has_trip_access((select auth.uid()), trip_id)
    )
  );

CREATE POLICY rag_documents_insert_authenticated
  ON public.rag_documents
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = (select auth.uid())
    AND (
      trip_id IS NULL
      OR public.user_has_trip_edit_access((select auth.uid()), trip_id)
    )
    AND (
      chat_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM public.chat_sessions cs
        WHERE cs.id = chat_id
          AND cs.user_id = (select auth.uid())
      )
    )
  );

CREATE POLICY rag_documents_update_authenticated
  ON public.rag_documents
  FOR UPDATE
  TO authenticated
  USING (
    user_id = (select auth.uid())
    AND (
      trip_id IS NULL
      OR public.user_has_trip_edit_access((select auth.uid()), trip_id)
    )
    AND (
      chat_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM public.chat_sessions cs
        WHERE cs.id = chat_id
          AND cs.user_id = (select auth.uid())
      )
    )
  )
  WITH CHECK (
    user_id = (select auth.uid())
    AND (
      trip_id IS NULL
      OR public.user_has_trip_edit_access((select auth.uid()), trip_id)
    )
    AND (
      chat_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM public.chat_sessions cs
        WHERE cs.id = chat_id
          AND cs.user_id = (select auth.uid())
      )
    )
  );

CREATE POLICY rag_documents_delete_authenticated
  ON public.rag_documents
  FOR DELETE
  TO authenticated
  USING (
    user_id = (select auth.uid())
    AND (
      trip_id IS NULL
      OR public.user_has_trip_edit_access((select auth.uid()), trip_id)
    )
  );

CREATE POLICY rag_documents_service_all
  ON public.rag_documents
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

ALTER TABLE public.saved_places ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS saved_places_select_trip_access ON public.saved_places;
DROP POLICY IF EXISTS saved_places_insert_trip_edit ON public.saved_places;
DROP POLICY IF EXISTS saved_places_update_trip_edit ON public.saved_places;
DROP POLICY IF EXISTS saved_places_delete_trip_edit ON public.saved_places;
DROP POLICY IF EXISTS saved_places_service_all ON public.saved_places;

CREATE POLICY saved_places_select_trip_access
  ON public.saved_places
  FOR SELECT
  TO authenticated
  USING (public.user_has_trip_access((select auth.uid()), trip_id));

CREATE POLICY saved_places_insert_trip_edit
  ON public.saved_places
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = (select auth.uid())
    AND public.user_has_trip_edit_access((select auth.uid()), trip_id)
  );

CREATE POLICY saved_places_update_trip_edit
  ON public.saved_places
  FOR UPDATE
  TO authenticated
  USING (public.user_has_trip_edit_access((select auth.uid()), trip_id))
  WITH CHECK (public.user_has_trip_edit_access((select auth.uid()), trip_id));

CREATE POLICY saved_places_delete_trip_edit
  ON public.saved_places
  FOR DELETE
  TO authenticated
  USING (public.user_has_trip_edit_access((select auth.uid()), trip_id));

CREATE POLICY saved_places_service_all
  ON public.saved_places
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

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

ALTER TABLE memories.sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "memories_sessions_owner" ON memories.sessions;
CREATE POLICY memories_sessions_owner ON memories.sessions FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS memories_sessions_service_all ON memories.sessions;
CREATE POLICY memories_sessions_service_all ON memories.sessions FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE memories.turns ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "memories_turns_owner" ON memories.turns;
CREATE POLICY memories_turns_owner ON memories.turns FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS memories_turns_service_all ON memories.turns;
CREATE POLICY memories_turns_service_all ON memories.turns FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE memories.turn_embeddings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "memories_turn_embeddings_owner" ON memories.turn_embeddings;
CREATE POLICY memories_turn_embeddings_owner ON memories.turn_embeddings FOR ALL TO authenticated USING (
  turn_id IN (SELECT id FROM memories.turns WHERE user_id = auth.uid())
) WITH CHECK (
  turn_id IN (SELECT id FROM memories.turns WHERE user_id = auth.uid())
);
DROP POLICY IF EXISTS memories_turn_embeddings_service_all ON memories.turn_embeddings;
CREATE POLICY memories_turn_embeddings_service_all ON memories.turn_embeddings FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Explicit grants for PostgREST roles (custom schemas do not always inherit usage privileges).
GRANT USAGE ON SCHEMA memories TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA memories TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA memories TO service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA memories TO authenticated, service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA memories
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA memories
  GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA memories
  GRANT USAGE, SELECT ON SEQUENCES TO authenticated, service_role;

ALTER TABLE public.search_destinations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "search_destinations_owner" ON public.search_destinations;
CREATE POLICY search_destinations_owner ON public.search_destinations FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

ALTER TABLE public.search_activities ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "search_activities_owner" ON public.search_activities;
CREATE POLICY search_activities_owner ON public.search_activities FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

ALTER TABLE public.search_flights ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "search_flights_owner" ON public.search_flights;
CREATE POLICY search_flights_owner ON public.search_flights FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

ALTER TABLE public.search_hotels ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "search_hotels_owner" ON public.search_hotels;
CREATE POLICY search_hotels_owner ON public.search_hotels FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

ALTER TABLE public.file_processing_queue ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "fpq_all_service" ON public.file_processing_queue;
CREATE POLICY fpq_all_service ON public.file_processing_queue FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE public.file_versions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "file_versions_all_service" ON public.file_versions;
CREATE POLICY file_versions_all_service ON public.file_versions FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE public.agent_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_config_versions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "agent_config_service_all" ON public.agent_config;
CREATE POLICY agent_config_service_all ON public.agent_config FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "agent_config_versions_service_all" ON public.agent_config_versions;
CREATE POLICY agent_config_versions_service_all ON public.agent_config_versions FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "agent_config_admin_all" ON public.agent_config;
CREATE POLICY agent_config_admin_all ON public.agent_config FOR ALL TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());
DROP POLICY IF EXISTS "agent_config_versions_admin_all" ON public.agent_config_versions;
CREATE POLICY agent_config_versions_admin_all ON public.agent_config_versions FOR ALL TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

-- Storage policies for buckets

-- Attachments bucket: metadata-first uploads + trip-collaboration reads.
DROP POLICY IF EXISTS "Users can upload attachments to their trips" ON storage.objects;
DROP POLICY IF EXISTS "Users can view attachments from accessible trips" ON storage.objects;
DROP POLICY IF EXISTS "Users can view attachments they own by record" ON storage.objects;
DROP POLICY IF EXISTS "Users can update their own attachments" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete their own attachments" ON storage.objects;

DROP POLICY IF EXISTS attachments_insert_by_record ON storage.objects;
DROP POLICY IF EXISTS attachments_select_by_record ON storage.objects;
DROP POLICY IF EXISTS attachments_update_by_record_owner ON storage.objects;
DROP POLICY IF EXISTS attachments_delete_by_record_owner ON storage.objects;

CREATE POLICY attachments_insert_by_record
  ON storage.objects
  FOR INSERT
  TO authenticated
  WITH CHECK (
    bucket_id = 'attachments'
    AND EXISTS (
      SELECT 1
      FROM public.file_attachments fa
      WHERE fa.file_path = name
        AND fa.user_id = (select auth.uid())
        AND fa.upload_status = 'uploading'
        AND fa.created_at > (now() - interval '15 minutes')
    )
  );

CREATE POLICY attachments_select_by_record
  ON storage.objects
  FOR SELECT
  TO authenticated
  USING (
    bucket_id = 'attachments'
    AND EXISTS (
      SELECT 1
      FROM public.file_attachments fa
      WHERE fa.file_path = name
        AND (
          fa.user_id = (select auth.uid())
          OR (
            fa.trip_id IS NOT NULL
            AND public.user_has_trip_access((select auth.uid()), fa.trip_id)
          )
        )
    )
  );

CREATE POLICY attachments_update_by_record_owner
  ON storage.objects
  FOR UPDATE
  TO authenticated
  USING (
    bucket_id = 'attachments'
    AND EXISTS (
      SELECT 1
      FROM public.file_attachments fa
      WHERE fa.file_path = name
        AND fa.user_id = (select auth.uid())
    )
  )
  WITH CHECK (
    bucket_id = 'attachments'
    AND EXISTS (
      SELECT 1
      FROM public.file_attachments fa
      WHERE fa.file_path = name
        AND fa.user_id = (select auth.uid())
    )
  );

CREATE POLICY attachments_delete_by_record_owner
  ON storage.objects
  FOR DELETE
  TO authenticated
  USING (
    bucket_id = 'attachments'
    AND EXISTS (
      SELECT 1
      FROM public.file_attachments fa
      WHERE fa.file_path = name
        AND fa.user_id = (select auth.uid())
    )
  );

DROP POLICY IF EXISTS "Anyone can view avatars" ON storage.objects;
CREATE POLICY "Anyone can view avatars" ON storage.objects FOR SELECT TO public USING (bucket_id = 'avatars');

DROP POLICY IF EXISTS "Users can upload their own avatar" ON storage.objects;
CREATE POLICY "Users can upload their own avatar"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'avatars' AND (
    name = auth.uid()::TEXT || '.jpg' OR name = auth.uid()::TEXT || '.png' OR name = auth.uid()::TEXT || '.gif' OR name = auth.uid()::TEXT || '.webp' OR name = auth.uid()::TEXT || '.avif'
  )
);

DROP POLICY IF EXISTS "Users can update their own avatar" ON storage.objects;
CREATE POLICY "Users can update their own avatar"
ON storage.objects FOR UPDATE TO authenticated
USING (bucket_id = 'avatars' AND coalesce(owner_id::text, owner::text) = auth.uid()::text)
WITH CHECK (bucket_id = 'avatars' AND coalesce(owner_id::text, owner::text) = auth.uid()::text);

DROP POLICY IF EXISTS "Users can delete their own avatar" ON storage.objects;
CREATE POLICY "Users can delete their own avatar"
ON storage.objects FOR DELETE TO authenticated
USING (bucket_id = 'avatars' AND coalesce(owner_id::text, owner::text) = auth.uid()::text);

DROP POLICY IF EXISTS "Users can upload trip images" ON storage.objects;
CREATE POLICY "Users can upload trip images" ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'trip-images' AND public.user_has_trip_access(auth.uid(), public.extract_trip_id_from_path(name)));

DROP POLICY IF EXISTS "Users can view trip images" ON storage.objects;
CREATE POLICY "Users can view trip images" ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'trip-images' AND public.user_has_trip_access(auth.uid(), public.extract_trip_id_from_path(name))
);

DROP POLICY IF EXISTS "Users can update their trip images" ON storage.objects;
CREATE POLICY "Users can update their trip images" ON storage.objects FOR UPDATE TO authenticated
USING (
  bucket_id = 'trip-images' AND (
    coalesce(owner_id::text, owner::text) = auth.uid()::text OR
    public.user_has_trip_access(auth.uid(), public.extract_trip_id_from_path(name))
  )
)
WITH CHECK (
  bucket_id = 'trip-images' AND (
    coalesce(owner_id::text, owner::text) = auth.uid()::text OR
    public.user_has_trip_access(auth.uid(), public.extract_trip_id_from_path(name))
  )
);

DROP POLICY IF EXISTS "Users can delete trip images" ON storage.objects;
CREATE POLICY "Users can delete trip images" ON storage.objects FOR DELETE TO authenticated
USING (
  bucket_id = 'trip-images' AND (
    coalesce(owner_id::text, owner::text) = auth.uid()::text OR
    public.user_has_trip_access(auth.uid(), public.extract_trip_id_from_path(name))
  )
);

DROP POLICY IF EXISTS "Service role has full access" ON storage.objects;
CREATE POLICY "Service role has full access" ON storage.objects TO service_role USING (true) WITH CHECK (true);

-- Realtime authorization (broadcast/presence)
DO $do$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'realtime'
      AND table_name = 'messages'
  ) THEN
    EXECUTE 'ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY';

    -- trip:{id}
    EXECUTE 'DROP POLICY IF EXISTS "rtm_trip_topic_read" ON realtime.messages';
    EXECUTE 'DROP POLICY IF EXISTS "rtm_trip_topic_write" ON realtime.messages';

    EXECUTE $pol$
      CREATE POLICY "rtm_trip_topic_read"
      ON realtime.messages
      FOR SELECT
      TO authenticated
      USING (
        realtime.topic() ~ '^trip:[0-9]+$'
        AND public.user_has_trip_access(auth.uid(), public.try_cast_bigint(public.rt_topic_suffix()))
        AND realtime.messages.extension IN ('broadcast', 'presence')
      )
    $pol$;

    EXECUTE $pol$
      CREATE POLICY "rtm_trip_topic_write"
      ON realtime.messages
      FOR INSERT
      TO authenticated
      WITH CHECK (
        realtime.topic() ~ '^trip:[0-9]+$'
        AND public.user_has_trip_access(auth.uid(), public.try_cast_bigint(public.rt_topic_suffix()))
        AND realtime.messages.extension IN ('broadcast', 'presence')
      )
    $pol$;

    -- user:{uuid}
    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'realtime'
        AND tablename = 'messages'
        AND policyname = 'rtm_user_topic_read'
    ) THEN
      EXECUTE $pol$
        CREATE POLICY "rtm_user_topic_read"
        ON realtime.messages
        FOR SELECT
        TO authenticated
        USING (
          realtime.topic() ~* '^user:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
          AND public.rt_topic_suffix() = auth.uid()::text
          AND realtime.messages.extension IN ('broadcast', 'presence')
        )
      $pol$;
    END IF;

    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'realtime'
        AND tablename = 'messages'
        AND policyname = 'rtm_user_topic_write'
    ) THEN
      EXECUTE $pol$
        CREATE POLICY "rtm_user_topic_write"
        ON realtime.messages
        FOR INSERT
        TO authenticated
        WITH CHECK (
          realtime.topic() ~* '^user:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
          AND public.rt_topic_suffix() = auth.uid()::text
          AND realtime.messages.extension IN ('broadcast', 'presence')
        )
      $pol$;
    END IF;

    -- session:{uuid}
    IF EXISTS (
      SELECT 1
      FROM information_schema.tables
      WHERE table_schema = 'public'
        AND table_name = 'chat_sessions'
    ) THEN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'realtime'
          AND tablename = 'messages'
          AND policyname = 'rtm_session_topic_read'
      ) THEN
        EXECUTE $pol$
          CREATE POLICY "rtm_session_topic_read"
          ON realtime.messages
          FOR SELECT
          TO authenticated
          USING (
            realtime.topic() ~* '^session:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            AND public.rt_is_session_member()
            AND realtime.messages.extension IN ('broadcast', 'presence')
          )
        $pol$;
      END IF;

      IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'realtime'
          AND tablename = 'messages'
          AND policyname = 'rtm_session_topic_write'
      ) THEN
        EXECUTE $pol$
          CREATE POLICY "rtm_session_topic_write"
          ON realtime.messages
          FOR INSERT
          TO authenticated
          WITH CHECK (
            realtime.topic() ~* '^session:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            AND public.rt_is_session_member()
            AND realtime.messages.extension IN ('broadcast', 'presence')
          )
        $pol$;
      END IF;
    END IF;
  END IF;
END $do$;

-- ===========================
-- REALTIME PUBLICATION
-- ===========================
DROP PUBLICATION IF EXISTS supabase_realtime CASCADE;
CREATE PUBLICATION supabase_realtime;
ALTER PUBLICATION supabase_realtime ADD TABLE public.trips, public.trip_collaborators, public.itinerary_items, public.chat_sessions, public.chat_messages, public.chat_tool_calls, public.bookings, public.flights, public.accommodations, public.saved_places, public.file_attachments;

-- ===========================
-- DATABASE CONFIG DEFAULTS (override in ops)
-- ===========================
DO $$
BEGIN
  BEGIN
    EXECUTE format(
      'ALTER DATABASE %I SET app.vercel_webhook_trips = %L',
      current_database(),
      ''
    );
    EXECUTE format(
      'ALTER DATABASE %I SET app.vercel_webhook_cache = %L',
      current_database(),
      ''
    );
    EXECUTE format(
      'ALTER DATABASE %I SET app.webhook_hmac_secret = %L',
      current_database(),
      ''
    );
  EXCEPTION
    WHEN insufficient_privilege THEN
      RAISE NOTICE 'Skipping ALTER DATABASE app.* settings (insufficient privilege)';
  END;
END;
$$;

-- ===========================
-- COMMENTS
-- ===========================
COMMENT ON TABLE public.bookings IS 'Stores accommodation booking confirmations for Amadeus + Stripe stack';
COMMENT ON COLUMN public.bookings.provider_booking_id IS 'Provider confirmation / booking identifier';
COMMENT ON COLUMN public.accommodation_embeddings.embedding IS 'pgvector (1536-d) for semantic search';

-- Done.
