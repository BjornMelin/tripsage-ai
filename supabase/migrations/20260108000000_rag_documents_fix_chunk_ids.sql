-- RAG documents: normalize chunk-suffixed IDs and ensure a composite primary key when needed.
-- Generated: 2026-01-08
--
-- Why:
-- - A recent change accidentally wrote chunk rows with `id = '<documentId>:<chunkIndex>'` while
--   upsert deduplicates on (id, chunk_index). This creates duplicate/stale rows on reindex.
-- - Some environments may also have an incorrect PRIMARY KEY on `id` only, which makes chunking
--   impossible. This migration makes that configuration safe by converting to a composite PK.
--
-- Safe to rerun: yes (idempotent checks).

BEGIN;
SET LOCAL lock_timeout = '30s';

-- 1) If the table has an incorrect PRIMARY KEY on `id` only, convert to a composite PK (id, chunk_index).
DO $do$
DECLARE
  v_pk_cols text[];
  v_table regclass;
  v_pk_name text;
BEGIN
  SELECT to_regclass('public.rag_documents')
  INTO v_table;

  IF v_table IS NULL THEN
    RETURN;
  END IF;

  SELECT c.conname
  INTO v_pk_name
  FROM pg_constraint c
  WHERE c.conrelid = v_table
    AND c.contype = 'p';

  SELECT array_agg(a.attname ORDER BY array_position(i.indkey, a.attnum))
  INTO v_pk_cols
  FROM pg_index i
  JOIN pg_attribute a
    ON a.attrelid = i.indrelid
   AND a.attnum = ANY (i.indkey)
  WHERE i.indrelid = v_table
    AND i.indisprimary;

  IF v_pk_cols = ARRAY['id'] THEN
    IF v_pk_name IS NOT NULL THEN
      EXECUTE format('ALTER TABLE public.rag_documents DROP CONSTRAINT IF EXISTS %I', v_pk_name);
    END IF;
  END IF;

  IF v_pk_cols IS NULL OR v_pk_cols = ARRAY['id'] THEN
    -- Ensure chunk_index column exists before proceeding.
    IF NOT EXISTS (
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = 'rag_documents'
        AND column_name = 'chunk_index'
    ) THEN
      RAISE NOTICE 'rag_documents.chunk_index column missing, skipping PK migration';
      RETURN;
    END IF;

    UPDATE public.rag_documents
    SET chunk_index = 0
    WHERE chunk_index IS NULL;

    ALTER TABLE public.rag_documents
      ALTER COLUMN chunk_index SET DEFAULT 0,
      ALTER COLUMN chunk_index SET NOT NULL;

    -- Add explicit constraint to avoid promoting a mismatched pre-existing index by name.
    ALTER TABLE public.rag_documents
      ADD CONSTRAINT rag_documents_pkey PRIMARY KEY (id, chunk_index);
  END IF;
END;
$do$;

-- 2) Normalize chunk-suffixed IDs:
--    - Identify rows whose `id` ends with `:<digits>` and those digits match `chunk_index`.
--    - Upsert them into the canonical `(id, chunk_index)` key using the base id (without suffix).
--    - Delete the chunk-suffixed rows.
DO $do$
DECLARE
  v_id_type text;
  v_id_expr text;
  v_uuid_guard_sql text;
  v_upserted bigint;
  v_deleted bigint;
BEGIN
  SELECT c.udt_name
  INTO v_id_type
  FROM information_schema.columns c
  WHERE c.table_schema = 'public'
    AND c.table_name = 'rag_documents'
    AND c.column_name = 'id';

  -- If the table is missing (shouldn't happen in prod), skip safely.
  IF v_id_type IS NULL THEN
    RETURN;
  END IF;

  -- If chunk_index is missing, DO #1 already skipped PK migration; skip normalization too.
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'rag_documents'
      AND column_name = 'chunk_index'
  ) THEN
    RAISE NOTICE 'rag_documents.chunk_index column missing, skipping ID normalization';
    RETURN;
  END IF;

  -- Build an expression to convert the extracted base id into the target column type.
  -- `id` is expected to be UUID in most environments, but may be TEXT in some.
  v_id_expr := CASE
    WHEN v_id_type = 'uuid' THEN
      'CASE WHEN b.base_id_text ~* ''^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'' THEN b.base_id_text::uuid ELSE NULL END'
    ELSE 'b.base_id_text'
  END;

  -- When `id` is UUID, prevent invalid base IDs from aborting the migration on `::uuid`.
  v_uuid_guard_sql := CASE
    WHEN v_id_type = 'uuid' THEN
      'AND regexp_replace(d.id::text, '':([0-9]+)$'', '''') ~* ''^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'''
    ELSE ''
  END;

  EXECUTE format($sql$
    WITH bad AS (
      SELECT
        d.id AS bad_id,
        d.chunk_index,
        regexp_replace(d.id::text, ':([0-9]+)$', '') AS base_id_text
      FROM public.rag_documents d
      WHERE d.chunk_index IS NOT NULL
        AND d.id::text ~ ':([0-9]+)$'
        -- Limit suffix length to 9 digits (max 999,999,999) to avoid unexpected large values.
        AND length(substring(d.id::text from ':([0-9]+)$')) <= 9
        AND substring(d.id::text from ':([0-9]+)$')::bigint = d.chunk_index
        %s
    ),
    upserted AS (
      INSERT INTO public.rag_documents (
        id,
        chunk_index,
        content,
        embedding,
        metadata,
        namespace,
        source_id,
        user_id,
        trip_id,
        chat_id,
        created_at,
        updated_at
      )
      SELECT
        %s,
        d.chunk_index,
        d.content,
        d.embedding,
        d.metadata,
        d.namespace,
        d.source_id,
        d.user_id,
        d.trip_id,
        d.chat_id,
        d.created_at,
        d.updated_at
      FROM public.rag_documents d
      JOIN bad b
        ON b.bad_id = d.id
       AND b.chunk_index = d.chunk_index
      ON CONFLICT (id, chunk_index) DO UPDATE
        SET content = CASE
              WHEN public.rag_documents.updated_at >= EXCLUDED.updated_at THEN public.rag_documents.content
              ELSE EXCLUDED.content
            END,
            embedding = CASE
              WHEN public.rag_documents.updated_at >= EXCLUDED.updated_at THEN public.rag_documents.embedding
              ELSE EXCLUDED.embedding
            END,
            metadata = CASE
              WHEN public.rag_documents.updated_at >= EXCLUDED.updated_at THEN public.rag_documents.metadata
              ELSE EXCLUDED.metadata
            END,
            namespace = CASE
              WHEN public.rag_documents.updated_at >= EXCLUDED.updated_at THEN public.rag_documents.namespace
              ELSE EXCLUDED.namespace
            END,
            source_id = CASE
              WHEN public.rag_documents.updated_at >= EXCLUDED.updated_at THEN public.rag_documents.source_id
              ELSE EXCLUDED.source_id
            END,
            user_id = CASE
              WHEN public.rag_documents.updated_at >= EXCLUDED.updated_at THEN public.rag_documents.user_id
              ELSE EXCLUDED.user_id
            END,
            trip_id = CASE
              WHEN public.rag_documents.updated_at >= EXCLUDED.updated_at THEN public.rag_documents.trip_id
              ELSE EXCLUDED.trip_id
            END,
            chat_id = CASE
              WHEN public.rag_documents.updated_at >= EXCLUDED.updated_at THEN public.rag_documents.chat_id
              ELSE EXCLUDED.chat_id
            END,
            created_at = LEAST(public.rag_documents.created_at, EXCLUDED.created_at),
            updated_at = GREATEST(public.rag_documents.updated_at, EXCLUDED.updated_at)
      RETURNING 1
    ),
    deleted AS (
      DELETE FROM public.rag_documents d
      USING bad b
      WHERE d.id = b.bad_id
        AND d.chunk_index = b.chunk_index
      RETURNING 1
    )
    SELECT
      (SELECT count(*) FROM upserted),
      (SELECT count(*) FROM deleted);
  $sql$, v_uuid_guard_sql, v_id_expr)
  INTO v_upserted, v_deleted;

  RAISE NOTICE 'rag_documents migration: upserted=%, deleted=%', v_upserted, v_deleted;
END;
$do$;

COMMIT;
